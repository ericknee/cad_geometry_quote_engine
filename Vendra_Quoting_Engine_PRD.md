# Product Requirements Document: CAD Geometry Engine & Quote App

| Field | Value |
|---|---|
| Product | Vendra Mini Quoting Engine |
| Source | Vendra Software Engineering Coding Challenge (Rev Jun 16 2026) |
| Timebox | 3 full-time days |
| Status | Draft |
| Material in scope | 6061 Aluminum |
| Process in scope | CNC machining (Haas-class machines) |

---

## 1. Overview

Vendra helps engineers get custom parts made cheaper and faster by automating manufacturing sourcing. A core piece of that is an instant quoting engine that reads a 3D CAD file and estimates manufacturing cost in real time.

This product is a small but runnable version of that workflow: a user uploads a `.step` file, enters a quantity, and receives an explainable CNC machining quote for 6061 aluminum. Every quote is stored and visible in a lightweight RFQ dashboard. The geometry analysis lives in a standalone engine that can be run from the command line, independent of the web app, and the web backend reuses that same engine.

## 2. Problem Statement

Engineers sourcing custom parts often wait days for manual quotes. An instant quote requires two things that are hard to get right: reliable extraction of manufacturing-relevant geometry from real CAD data, and a pricing model that turns that geometry into a credible, explainable price and lead time. This project demonstrates both, wrapped in a product experience that feels real.

## 3. Goals and Non-Goals

### 3.1 Goals

1. Parse real `.step` files and compute bounding box, volume, surface area, and at least one complexity proxy.
2. Expose geometry analysis as a standalone CLI that outputs JSON, reusable as a library by the backend.
3. Produce a quote with per-unit cost, total cost, lead time, cost breakdown, and geometry summary.
4. Persist every quote and display history in a simple dashboard with status management.
5. Keep geometry, pricing, API, and persistence cleanly separated.
6. Make the pricing model transparent and roughly calibrated against competitor quotes.
7. Deliver a clear, usable, polished-feeling UI.
8. Make it trivial to run locally (README; Docker Compose as a bonus).
9. Record why each significant decision was made, including decisions proposed by AI tools, so the evaluator can follow the reasoning.

### 3.2 Non-Goals

Authentication, payments, multi-user permissions, production deployment, a full ERP, a CAM/toolpath simulator, perfect feature recognition, exact CNC pricing, and materials or processes beyond 6061 aluminum CNC machining.

## 4. Users and Personas

| Persona | Need | Primary surfaces |
|---|---|---|
| **Design engineer** (requester) | Upload a part, get a fast, believable price and lead time, understand what drives cost. | Upload form, quote result |
| **Sourcing / ops reviewer** (Vendra internal) | Track incoming RFQs, review and change quote status. | Quote dashboard, quote detail |
| **Evaluator / developer** | Run geometry analysis on a file without the UI; inspect logic. | CLI, README, report |

## 5. User Stories

| ID | As a… | I want to… | So that… |
|---|---|---|---|
| US-1 | Engineer | upload a `.step` file and enter a quantity | I can request a quote |
| US-2 | Engineer | see per-unit cost, total cost, and lead time | I can decide whether to order |
| US-3 | Engineer | see a cost breakdown (material, machine time, setup) | I understand what drives the price |
| US-4 | Engineer | see a geometry summary of my part | I can confirm the file was read correctly |
| US-5 | Reviewer | see a list of past quotes | I can track RFQ volume and history |
| US-6 | Reviewer | open any past quote and see its full breakdown | I can review it in detail |
| US-7 | Reviewer | change a quote's status (new / quoted / reviewed / archived) | I can manage the pipeline |
| US-8 | Developer | run `python analyze_geometry.py <file.step>` from a terminal | I can verify geometry independently of the app |
| US-9 | Engineer | get a clear error for invalid or unreadable files | I know what to fix |

## 6. Product Flow

1. User opens the website.
2. User uploads a `.step` file.
3. User enters a quantity.
4. User clicks **Generate Quote**.
5. Backend runs the geometry engine on the file.
6. Backend runs the pricing and lead-time models on the geometry.
7. Backend saves the quote to the database (status `quoted`).
8. Frontend displays the quote result.
9. User can navigate to the dashboard to view and manage previous quotes.

```
[Browser] --upload .step + qty--> [API] --> [Geometry Engine] --> geometry JSON
                                     |                                  |
                                     |<------------ [Pricing Engine] <--+
                                     |
                                     +--> [MongoDB: quotes] --> [Dashboard]
```

## 7. Functional Requirements

### 7.1 Standalone Geometry Engine (Core Requirement)

**FR-G1. Runnable independently.** A command such as `python analyze_geometry.py vendra-gear.step` (or equivalent) analyzes a file with no web server or database running.

**FR-G2. Shared logic.** The backend imports and calls the same geometry module. There is exactly one implementation of geometry analysis.

**FR-G3. Required measurements.**

| Output | Unit | Method (recommended) |
|---|---|---|
| Bounding box length / width / height | mm | Axis-aligned bounding box of the solid; sorted so length ≥ width ≥ height. Optionally also compute an oriented (minimal) bounding box. |
| Volume | cm³ | Mass properties of the solid (OpenCascade `GProp_GProps`). |
| Surface area | cm² | Surface properties of all faces. |

**FR-G4. Complexity features.** At least one is required; the target set is:

| Feature | Heuristic |
|---|---|
| Face count | Count `TopoDS_Face` entities. |
| Edge count | Count unique `TopoDS_Edge` entities. |
| Cylindrical faces | Count faces whose underlying surface is a cylinder. |
| Holes detected | Group internal (concave) cylindrical faces by shared axis and radius; each group is one hole. Distinguish internal from external cylinders using face orientation / normal direction relative to the axis. |
| Surface-area-to-volume ratio | `surface_area_cm2 / volume_cm3`. |
| Material removal ratio | `1 − part_volume / stock_volume`. |
| Complexity score | Weighted, normalized combination of the above, clamped to a sane range (e.g., 1.0–3.0). |

**FR-G5. Output format.** JSON to stdout, with an optional `--pretty` flag and a `--out file.json` flag. Minimum schema:

```json
{
  "file": "vendra-gear.step",
  "units": "mm",
  "bounding_box_mm": { "length": 23.37, "width": 22.56, "height": 12.32 },
  "stock_volume_cm3": 6.50,
  "volume_cm3": 1.95,
  "surface_area_cm2": 0.0,
  "features": {
    "face_count": 0,
    "edge_count": 0,
    "cylindrical_faces": 0,
    "holes_detected": 0,
    "sa_to_volume_ratio": 0.0,
    "material_removal_ratio": 0.0,
    "complexity_score": 1.0
  },
  "warnings": []
}
```

(Values above are illustrative; the bounding box and volume match the competitor's reported measurements for the sample gear.)

**FR-G6. Error handling.** Non-zero exit code and a JSON error message for: missing file, unsupported extension, unreadable STEP, zero solids, or invalid/non-closed solid. Multiple solids are either merged or reported with a warning.

**FR-G7. Units.** STEP files may be authored in inches or mm. The engine must normalize to mm internally and report the source unit if detectable.

### 7.2 Pricing Engine

A pure, side-effect-free module: `price(geometry, quantity, config) -> cost_breakdown`. All constants live in a single config object so they can be tuned during calibration.

**Baseline constants (given):**

| Variable | Value |
|---|---|
| Material | 6061 Aluminum |
| Density | 2.7 g/cm³ |
| Aluminum price | $5.00/kg |
| Machine | Haas CNC |
| Machining rate | $100/hour |

**FR-P1. Material cost.** Use **stock volume**, not part volume, because a shop buys and cuts raw stock, not the finished shape. Stock = bounding box plus a machining allowance on each side (e.g., +3 mm per side), optionally rounded up to standard bar/plate sizes.

```
stock_volume_cm3   = (L + 2a)(W + 2a)(H + 2a) / 1000
material_cost_unit = stock_volume_cm3 × 2.7 g/cm³ / 1000 × $5.00/kg
```

A **$10 minimum material charge** applies per unit to reflect real-world minimum stock purchases, saw cuts, and material handling:

```
material_cost_unit = max(computed_material_cost_unit, $10.00)
```

The breakdown reports both the computed value and whether the minimum was applied.

**Documentation requirement:** The challenge requires an explanation whenever stock volume is used instead of part volume. The README and report must state why stock volume was chosen (shops buy and cut raw stock, so the removed material is paid for too), the allowance used, and the rationale for the $10 minimum.

**FR-P2. Machine time.**

```
removed_volume_cm3   = stock_volume − part_volume
roughing_minutes     = removed_volume_cm3 / MRR_rough      (MRR in cm³/min for 6061)
finishing_minutes    = surface_area_cm2 / finish_rate      (cm²/min)
hole_minutes         = holes_detected × minutes_per_hole
handling_minutes     = per-part load/unload/flip constant
cycle_minutes        = (roughing + finishing + hole + handling) × complexity_score
```

```
machine_cost_unit = cycle_minutes / 60 × $100/hr      (undiscounted)
```

**FR-P3. Quantity discounts.** The discount rate is taken from the per-unit machine cost, but it is applied **only at the total price calculation** (FR-P5). Machine time itself is never reduced, so lead time and all other time-based figures use undiscounted hours.

| Quantity | Discount on per-unit machine cost |
|---|---|
| 1–5 | 0% |
| 6–20 | 10% |
| 21–100 | 20% |
| 101+ | 30% |

The source lists "21 to 100" and "100+", which overlap at 100. This PRD resolves the overlap by placing qty 100 in the 20% tier.

**FR-P4. Setup cost.** Fixed setup hours (CAM programming, fixturing, first-article), scaled modestly by complexity and number of setups, amortized over quantity:

```
setup_hours        = base_setup_hours × setup_complexity_factor
setup_cost_unit    = setup_hours × $100 / quantity
```

**FR-P5. Totals.**

```
quantity_discount_unit = machine_cost_unit × discount_rate
total_cost_per_unit    = material_cost_unit + machine_cost_unit + setup_cost_unit − quantity_discount_unit
total_order_cost       = total_cost_per_unit × quantity
```

The breakdown shows the quantity discount as its own line, so the undiscounted machine cost stays visible.

All money values are rounded to cents only at output time.

**FR-P6. Explainability.** The breakdown response includes intermediate values (stock volume, removed volume, computed material cost and whether the $10 minimum applied, undiscounted cycle minutes, discount rate and amount, setup hours) so the UI and README can explain every number.

### 7.3 Lead Time Model

```
lead_time_days = min_lead_time
               + ceil(total_machine_hours / productive_hours_per_day)
               + complexity_buffer
```

| Term | Definition |
|---|---|
| `min_lead_time` | 5 business days (queue, material, QA, shipping prep). |
| `total_machine_hours` | setup hours + cycle hours × quantity, using **undiscounted** cycle hours. Discounts are pricing only and never shorten lead time. |
| `productive_hours_per_day` | e.g., 8 hours on one machine. |
| `complexity_buffer` | 0 / 1 / 2 days by complexity score band. |

Output is an integer number of business days.

### 7.4 Backend API

Separation of concerns:

| Layer | Responsibility |
|---|---|
| `geometry/` | STEP parsing and feature extraction (shared with CLI). |
| `pricing/` | Cost and lead-time models, config constants. |
| `api/` | HTTP routing, validation, file handling, orchestration. |
| `db/` | MongoDB models and repository functions. |

**Endpoints:**

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| `POST` | `/api/quotes` | Create quote | `multipart/form-data`: `file` (.step/.stp), `quantity` (int ≥ 1) | 201 + full quote document |
| `GET` | `/api/quotes` | List quotes | Optional `status`, `limit`, `skip` | Array of quote summaries, newest first |
| `GET` | `/api/quotes/{id}` | Quote detail | — | Full quote document |
| `PATCH` | `/api/quotes/{id}/status` | Update status | `{ "status": "reviewed" }` | Updated quote |
| `GET` | `/api/health` | Health check | — | `{ "ok": true }` |

Optional: `POST /api/quotes/{id}/requote` with a new quantity, reusing stored geometry.

**Validation and errors:** file extension check, max upload size (e.g., 50 MB), quantity integer 1–10,000, invalid status rejected, consistent error shape `{ "error": { "code", "message" } }`, 422 for unparseable CAD.

**Processing:** Geometry analysis may take seconds on complex parts. For the 3-day scope, synchronous processing with a frontend loading state is acceptable; async jobs are a stretch goal.

### 7.5 Database and Quote Dashboard

MongoDB (preferred) with a single `quotes` collection.

**Quote document schema:**

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Quote ID |
| `file_name` | string | Original upload name |
| `file_path` / `file_hash` | string | Stored file location and SHA-256 (enables caching geometry by hash) |
| `quantity` | int | |
| `material` | string | `"6061 Aluminum"` |
| `geometry` | object | Bounding box, volume, surface area, stock volume |
| `features` | object | Face/edge counts, holes, ratios, complexity score |
| `cost_breakdown` | object | Per-unit material, machine (undiscounted), setup, quantity discount, total per unit, total order, plus intermediates |
| `lead_time_days` | int | |
| `status` | enum | `new`, `quoted`, `reviewed`, `archived` |
| `pricing_version` | string | Version of pricing config used, so old quotes remain explainable |
| `created_at` | datetime | |
| `updated_at` | datetime | |

Indexes: `created_at` (desc), `status`.

**Status lifecycle:** `new` (record created, analysis pending or failed) → `quoted` (analysis and pricing succeeded) → `reviewed` (human has looked at it) → `archived`. Any status may move to `archived`.

### 7.6 Frontend

**Pages:**

1. **New Quote** (home): drag-and-drop upload zone (accepts `.step`/`.stp`), quantity input (stepper, default 1), Generate Quote button, loading state during analysis, inline error messages.
2. **Quote Result** (`/quotes/[id]`): result card plus detail panels.
3. **Dashboard** (`/quotes`): table of past quotes.

**Quote result must show:**

| Section | Fields |
|---|---|
| Header | File name, quantity, material, status, created date |
| Headline price | Per-unit cost, total order cost, lead time (business days) |
| Cost breakdown | Material cost (flag when the $10 minimum applies), machine time cost, setup cost, quantity discount as its own line (per unit and per order) |
| Geometry | Bounding box L × W × H (mm, with inches toggle), volume, surface area |
| Complexity | Complexity score, holes detected, face count, edge count, SA:V ratio |

**Dashboard table columns:** file name, quantity, per-unit price, total, lead time, status (inline editable dropdown), created date, link to detail. Filter by status; sort by date.

**UX quality bar:** clear visual hierarchy with price front and center; responsive layout; empty, loading, and error states for every view; numbers formatted with units and currency; a stacked bar or simple chart showing the cost breakdown.

**Stretch:** in-browser 3D preview of the part (backend exports the STEP tessellation to GLB/STL; frontend renders with three.js / react-three-fiber); live re-pricing when quantity changes on the result page; a quantity-vs-unit-price curve (1, 10, 100).

### 7.7 Decision Log

The evaluator explicitly wants to understand the approach and why decisions were made (or why AI-suggested decisions were accepted). The repo must include a decision log (`DECISIONS.md`, or a section of the README) with one entry per significant decision.

Each entry records the decision, the alternatives considered, the reasoning, and whether it originated from an AI tool and why it was accepted or changed. At minimum, cover the geometry library, backend framework, database, stock volume vs. part volume, the $10 material minimum, the discount being applied only at totals, the qty 100 tier resolution, complexity score weights, and the calibration target (charged vs. list price).

## 8. Pricing Calibration

### 8.1 Competitor Reference Data

Sample part: `challenge-gear.STEP` (a small spur gear with a hub).

Competitor 1 reports the part as **23.37 × 22.56 × 12.32 mm**, volume **1,952.23 mm³ (≈1.95 cm³)**, 0 threads/tapped holes, ±0.005" tolerance, 125 µin Ra finish, standard inspection.

| Source | Qty | Option | Lead time | Price each (charged) | List price (struck through) |
|---|---|---|---|---|---|
| Competitor 1 | 1 | Made in USA, Expedite | 3 business days | $359.29 | $471.57 |
| Competitor 1 | 1 | Made in USA, Standard (selected) | 4 business days | $196.43 | $257.81 |
| Competitor 1 | 1 | Made in USA, Economy | 7 business days | $160.49 | $210.65 |
| Competitor 1 | 1 | Made Internationally, Economy | 7 business days | $97.26 | $127.66 |
| Competitor 2 | 1 | 6061 (T6/T651/T6511), as machined | — | $189.41 | — |
| Both | 10 | — | — | Provided separately (not in document) | — |
| Both | 100 | — | — | Provided separately (not in document) | — |

Every Competitor 1 price is shown as a discount of about 23.8% off a struck-through list price. **Calibration uses the charged (discounted) prices**, since that is what the customer actually pays and it agrees closely with Competitor 2 ($196.43 vs. $189.41). List prices are recorded for reference only.

### 8.2 Calibration Insights

1. **Material is negligible for this part.** Even using stock with a 3 mm allowance per side (≈29 × 29 × 18 mm ≈ 15 cm³ ≈ 41 g), computed material cost is roughly $0.20 at $5/kg, so the $10 minimum charge (FR-P1) applies. Even at $10, price is almost entirely setup plus machine time.
2. **US standard target of ~$190–$196 at qty 1, minus the $10 material minimum, implies ~1.8 hours of billed shop time at $100/hr.** A plausible split is ~1.25–1.5 hours of setup/programming plus ~0.3–0.5 hours of cycle time for a gear profile with a bore.
3. **Implication for quantity scaling:** with setup dominating, unit price should drop steeply from qty 1 to qty 10 and flatten toward cycle-time cost by qty 100. The qty 10 and qty 100 competitor numbers, once obtained, are the best check on the setup-vs-cycle split.
4. **Lead time:** the 5-business-day minimum in the challenge sits between the competitor's Standard (4) and Economy (7) tiers, which is reasonable.
5. **Gear teeth are the main complexity driver.** Many small faces and a high SA:V ratio should push the complexity score up; this is where feature weights should be tuned.

### 8.3 Calibration Process

1. Run the engine on the sample gear and record geometry.
2. Set constants (MRR, finish rate, setup hours, complexity weights) from shop-reasonable defaults.
3. Compare qty 1/10/100 outputs to competitor quotes; tune setup hours first (dominates qty 1), then cycle time (dominates qty 100).
4. Document final constants and the residual error per data point in the README.

**Target:** qty 1 price within ±25% of the charged US Standard / Competitor 2 band (~$150–$240). Competitor 1 list prices are not calibration targets.

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Runnability | Clone → follow README → working app in under 10 minutes. Docker Compose (`docker compose up`) as a bonus. |
| Performance | Sample gear analyzed and quoted in < 5 s on a laptop. |
| Reliability | Invalid files never crash the server; errors are returned cleanly. |
| Code quality | Typed interfaces between layers; pricing and geometry modules are pure and unit-tested. |
| Testability | Unit tests for geometry on simple known solids (e.g., a 10 mm cube: volume 1 cm³, area 6 cm², 6 faces, 12 edges; a plate with one through-hole: 1 hole) and for pricing math and discount tiers. |
| Explainability | Every number in a quote can be traced to a formula in the README. |
| Security (basic) | Sanitize filenames, cap upload size, store uploads outside web root. |

## 10. Recommended Technical Approach

| Component | Choice | Rationale |
|---|---|---|
| Geometry | Python + OpenCascade via `cadquery` / `OCP` (or `pythonocc-core`) | Industry-grade B-rep kernel; exact STEP parsing, mass properties, and surface type inspection. |
| Backend | Python FastAPI | Same language as geometry engine (direct import, no subprocess); auto OpenAPI docs; fast to build. |
| Database | MongoDB (via `motor` or `pymongo`) | Preferred by Vendra; quote documents are naturally nested JSON. |
| Frontend | Next.js (React) + TypeScript + Tailwind | Matches Vendra's stack; quick to make polished. |
| 3D preview (stretch) | react-three-fiber | Lightweight viewer for tessellated part. |
| Packaging | Docker Compose: `web`, `api`, `mongo` | One-command startup; avoids OCC install pain on host machines. |

**Suggested repo layout:**

```
/engine            geometry package + analyze_geometry.py CLI
/pricing           pricing + lead time models, config.py
/api               FastAPI app, routes, schemas
/db                Mongo models, repository
/web               Next.js frontend
/samples           vendra-gear.step
/tests             engine and pricing tests
docker-compose.yml
README.md
REPORT.md
DECISIONS.md
```

## 11. Delivery Plan (3 Days)

| Day | Focus | Exit criteria |
|---|---|---|
| **Day 1** | Geometry engine + CLI | CLI outputs correct bbox/volume/area on sample gear (matches competitor's reported 23.37 × 22.56 × 12.32 mm and 1.95 cm³); face/edge/cylinder/hole detection; unit tests on simple solids. |
| **Day 2** | Pricing, lead time, API, DB | Pricing module with config and tests; calibrated against qty 1 competitor data; all 4 endpoints working with MongoDB; Docker Compose for API + Mongo. |
| **Day 3** | Frontend + docs | Upload → quote → dashboard flow end to end; status editing; polish states; README, short report, and decision log; final calibration notes; stretch items if time allows. |

**Prioritization rule:** if time runs short, protect in order: (1) standalone engine correctness, (2) end-to-end quote flow, (3) README/report, (4) UI polish, (5) stretch features.

## 12. Acceptance Criteria

1. `python analyze_geometry.py samples/vendra-gear.step` prints valid JSON with bounding box, volume, surface area, and complexity features, with no server running.
2. The backend imports the same geometry module (no duplicated logic).
3. Uploading the sample file with quantity 1, 10, and 100 in the UI returns a quote with all required fields.
4. Each quote is saved in MongoDB and appears in the dashboard.
5. Quote detail is retrievable by ID and shows the full breakdown.
6. Status can be changed from the dashboard and the change persists.
7. Per-unit price decreases as quantity increases, reflecting setup amortization and discount tiers.
8. Invalid uploads (wrong extension, corrupt file, quantity 0) produce clear errors.
9. README covers what the app does, install, run (frontend, backend, DB, CLI), example flow, example output, assumptions, and limitations.
10. Report (1–2 pages) covers parsing, geometry, complexity, pricing, lead time, assumptions, and future improvements, and explains why stock volume is used instead of part volume.
11. A decision log (§7.7) explains the reasoning behind each significant decision, including AI-suggested ones.

## 13. Deliverables

1. GitHub repository with frontend, backend, geometry engine, pricing logic, and DB schema.
2. Standalone geometry CLI entry point.
3. README (sections listed in Acceptance Criterion 9).
4. Short report (in README or `REPORT.md`), including the stock-volume justification.
5. Decision log (`DECISIONS.md` or README section; see §7.7).
6. Optional Docker setup.
7. If incomplete: a note on what works, what is missing, and next steps.

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OpenCascade install issues across OSes | Reviewers can't run the engine | Use conda or Docker; pin versions; document both paths. |
| Hole detection false positives (gear tooth roots, fillets read as cylinders) | Inflated complexity | Require concave orientation, minimum arc span (near-full cylinder), and grouping by axis. |
| Unit mismatch (inch vs mm STEP) | Prices off by orders of magnitude | Read STEP units explicitly; sanity check against plausible part sizes; surface warnings. |
| Pricing overfit to one sample part | Poor generalization | Keep formula physically motivated (MRR, setup), not curve-fit; document limits. |
| Slow analysis on large files | Request timeouts | Loading state, timeout limits; async jobs as a documented future improvement. |

## 15. Assumptions

1. Single-part STEP files; one solid per file (multi-solid files flagged).
2. 3-axis machining on a Haas VMC; number of setups estimated from geometry (default 2 for a part like the gear).
3. Stock is rectangular bar/plate with a fixed per-side allowance.
4. Standard tolerance (±0.005") and as-machined finish; no threads, inserts, coatings, or inspection reports.
5. Machining rate of $100/hour covers labor and overhead; no separate margin line.
6. Lead time is in business days and assumes one machine dedicated to the order.
7. The example output in the challenge (82.4 × 82.4 × 12.7 mm gear) is illustrative; the actual sample part's competitor-reported dimensions are 23.37 × 22.56 × 12.32 mm.

## 16. Open Questions

1. Can Vendra share the qty 10 and qty 100 competitor quotes ("provided separately")? They are the key data for calibrating the setup vs cycle-time split.
2. Is the sample file named `vendra-gear.step` the same part as `challenge-gear.STEP` in the competitor screenshots?
3. Should the quote offer multiple lead-time tiers (expedite / standard / economy) like Competitor 1, or a single estimate?
4. Should a margin/markup be modeled on top of shop cost, or is $100/hr considered the fully loaded customer rate?
5. Should re-quoting a different quantity create a new record or a revision of the existing quote?

## 17. Future Improvements

1. True feature recognition: pockets, slots, thin walls, threads, undercuts, and minimum internal radius (tool-access analysis).
2. Setup count and orientation estimation from accessible face normals.
3. Toolpath-informed cycle time estimates (or integration with a CAM kernel).
4. Multiple materials, finishes, tolerances, and processes (sheet metal, 3D printing).
5. Lead-time tiers with price multipliers, mirroring competitor offerings.
6. Async job queue for large files; geometry caching by file hash.
7. 3D viewer with highlighted detected features (holes, thin walls) for transparency.
8. Data-driven calibration from historical quotes and won/lost outcomes.
