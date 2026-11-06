# Engine flow: geometry and quote estimation

Diagrams render on GitHub and in VS Code (Mermaid). Code lives in `backend/geometry/` and
`backend/pricing/`. Both are pure: no web, no database.

## 1. Big picture

```mermaid
flowchart LR
    A[".step file + quantity"] --> B["geometry<br/>analyze_file()"]
    B -->|GeometryResult| C["pricing<br/>price() + lead_time()"]
    C -->|CostBreakdown + LeadTime| D["quote"]
```

## 2. Geometry engine (STEP file in, GeometryResult out)

```mermaid
flowchart TD
    A[".step file"] --> L["loader.py<br/>read file, convert units to mm,<br/>reject missing / unreadable / zero solids"]
    L --> S["one or more solids"]
    S --> P["per solid: analyze_solid()"]

    P --> M["measures.py<br/>volume, surface area,<br/>bounding corners"]
    P --> F["features.py<br/>face count, edge count,<br/>cylindrical faces"]
    F --> H["holes.py<br/>holes_detected"]
    F --> ST["setups.py<br/>setups (clampings)"]

    M --> G["merge solids<br/>(sum volumes and areas,<br/>one box around all, warn if more than 1)"]
    F --> G
    H --> G
    ST --> G

    G --> X["derive from merged values"]
    X --> X1["bounding box L >= W >= H"]
    X --> X2["stock volume =<br/>(L+2a)(W+2a)(H+2a), a = 3 mm"]
    X --> X3["SA:V ratio"]
    X --> X4["material removal ratio =<br/>1 - volume / stock"]

    X1 --> R["GeometryResult"]
    X2 --> R
    X3 --> R
    X4 --> R
    X5 --> R
```

### What each feature means (plain language)

| Feature | Meaning | Why pricing cares |
|---|---|---|
| Bounding box | Smallest straight-edged box around the part | Sets the raw block size to buy |
| Stock volume | Bounding box plus 3 mm of extra on every side | Material is bought as a block, not as the finished shape |
| Volume | Space the metal takes up | Stock minus volume = metal cut away (roughing time) |
| Surface area | Total outside skin of the part | Every surface needs a finishing pass |
| Face | One continuous surface (a flat side, a curved wall) | Many small faces (gear teeth) = more machining detail |
| Hole | Cylinder wall with material around it, covering at least 270 deg of the circle | Drilling time per hole |
| Setup | One clamping of the part on a 3-axis machine | Each re-clamp costs operator time |
| Complexity score | Planned 1.0 to 3.0 multiplier for hard parts | **Not built yet** (pricing uses 1.0) |

### Hole rule

```mermaid
flowchart LR
    C["cylinder faces"] --> G["group by axis + radius"]
    G --> T{"material just outside the wall<br/>AND summed arc >= 270 deg?"}
    T -->|yes| Y["counts as 1 hole"]
    T -->|no| N["ignored: fillet, slot end,<br/>outside curve"]
```

### Setup rule (3-axis machine)

```mermaid
flowchart LR
    A["thinnest direction = main axis"] --> B["+1 for a flat face on top"]
    A --> C["+1 for a flat face on bottom"]
    A --> D["+1 per other axis that has<br/>holes pointing along it"]
    B --> E["setups = sum, minimum 1"]
    C --> E
    D --> E
```

Sample results: gear = 2, bracket = 4.

## 3. Quote estimation (GeometryResult + quantity in, CostBreakdown + LeadTime out)

All constants come from one `PricingConfig` (`pricing/config.py`).

```mermaid
flowchart TD
    GR["GeometryResult + quantity"] --> MAT
    GR --> CYC
    GR --> SET

    subgraph MAT["Material (per unit)"]
        M1["stock volume x 2.7 g/cm3 x $5/kg"] --> M2["max(computed, $10 minimum)"]
    end

    subgraph CYC["Machine time (per unit)"]
        C1["roughing = (stock - volume) / cm3 per min"]
        C2["finishing = surface area / cm2 per min"]
        C3["holes = holes x min per hole"]
        C4["handling = flat minutes per part"]
        C1 --> C5["sum x complexity score"]
        C2 --> C5
        C3 --> C5
        C4 --> C5
        C5 --> C6["cycle minutes / 60 x $100/h<br/>= machine cost (undiscounted)"]
    end

    subgraph SET["Setup (once per order)"]
        S1["setup hours = base x (1 + 0.25 x (setups - 1))"] --> S2["x $100/h, divided by quantity<br/>= setup cost per unit"]
    end

    QD["discount rate from quantity tier<br/>1-5: 0%, 6-20: 10%, 21-100: 20%, 101+: 30%"] --> DISC["discount = machine cost x rate<br/>(own line)"]
    C6 --> DISC

    M2 --> TOT
    C6 --> TOT
    S2 --> TOT
    DISC --> TOT["total per unit =<br/>material + machine + setup - discount"]
    TOT --> ORD["total order = per unit x quantity<br/>(round to cents only here)"]
```

### Lead time

```mermaid
flowchart LR
    A["setup hours<br/>+ cycle hours x quantity<br/>(undiscounted)"] --> M["machine days = hours / 8"]
    M --> B["work days = ceil(machine days)"]
    M --> E["buffer days = ceil(machine days<br/>x 0.5 x min(faces / 100, 1))"]
    B --> D["lead time days ="]
    C["5 day minimum"] --> D
    E --> D
```

Discounts never shorten lead time.

## 4. Open work

| Item | State |
|---|---|
| Pricing constants | Placeholders (roughing, finishing, per-hole, handling, base setup). Tune against competitor quotes: setup hours first (drives qty 1), then cycle time (drives qty 100). |
| Complexity buffer | Face count only; the 100-face cap and 50% max rate are assumptions from two samples. Setups and thin walls are not included. |
