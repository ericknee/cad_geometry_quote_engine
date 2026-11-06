# Vendra Quoting Engine

Upload a `.step` file, pick a quantity, get an explainable CNC quote for 6061 aluminum. See
`Vendra_Quoting_Engine_PRD.md` for requirements, `DECISIONS.md` for why things are built this way,
and `REPORT.md` for how parsing, pricing and lead time work.

> Status: geometry, pricing, lead time, API, worker and web pages are built. The **complexity score is
> not implemented yet** and the pricing is fitted to a single data point, the sample gear at qty 1 (see
> [Known limitations](#known-limitations)).

## What the app does

- Reads a `.step`/`.stp` CAD file with OpenCascade and measures the bounding box, volume, surface area,
  face and edge counts, and holes.
- Prices CNC machining of the part in 6061 aluminum: material, machine time and setup, with setup
  amortized over the quantity, plus a lead time in business days.
- Stores every quote in MongoDB and shows them in a dashboard where a reviewer can change the status.
- The geometry engine also runs on its own from the command line, with no server or database.

Parts of the repo:

| Folder | What it holds |
|---|---|
| `backend/geometry` | STEP parsing and measurements (shared by the CLI and the API) |
| `backend/pricing` | Cost and lead-time models; all constants in `config.py` |
| `backend/api` | FastAPI service, background worker, MongoDB access |
| `web` | Next.js frontend |
| `samples` | Sample STEP files |

## Install

You need:

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js (current LTS) and npm
- Docker (for MongoDB, or for the whole stack)

```bash
cp .env.example .env
uv sync                  # Python dependencies, including OpenCascade (cadquery-ocp)
cd web && npm install    # frontend dependencies
```

## Run locally

Run each of these in its own terminal, from the repo root unless noted.

```bash
# 1. Database: MongoDB on localhost:27017
docker compose up -d mongo

# 2. Backend API: http://localhost:8000/api/health
uv run python -m uvicorn api.main:app --reload --app-dir backend

# 3. Worker (required, see below)
uv run python -m api.worker

# 4. Frontend: http://localhost:3000
cd web && npm run dev
```

The **worker must be running** next to the API: the API only queues a quote, the worker analyzes the
file and prices it. Without a worker, quotes stay `queued`.

Or the whole stack in one command: `docker compose up --build` (mongo, api, worker, web).

## Geometry CLI (no server needed)

```bash
uv run python backend/analyze_geometry.py samples/vendra-gear.STEP
```

It prints one line of JSON and exits 0. On a bad file it prints a JSON error and exits non-zero.
Output for the sample gear (formatted here for reading):

```json
{
  "file": "vendra-gear.STEP",
  "units": "mm",
  "source_units": "inch",
  "material": "6061 Aluminum",
  "bounding_box_mm": { "length": 23.368, "width": 22.561, "height": 12.319 },
  "stock_volume_cm3": 15.366,
  "volume_cm3": 1.9522,
  "stock_mass_kg": 0.04149,
  "part_mass_kg": 0.00527,
  "surface_area_cm2": 14.212,
  "features": {
    "face_count": 99,
    "edge_count": 284,
    "cylindrical_faces": 70,
    "holes_detected": 1,
    "setups": 2,
    "thin_wall_count": 1,
    "sa_to_volume_ratio": 7.28,
    "material_removal_ratio": 0.873
  },
  "solids": 1,
  "warnings": []
}
```

## Example upload flow

1. Open http://localhost:3000.
2. Drop `samples/vendra-gear.STEP` on the upload area and set the quantity to 10.
3. Click **Generate Quote**. The page shows a loading state while the worker analyzes the file
   (about a second for the gear).
4. The quote page shows the per-unit price, order total, lead time, cost breakdown, geometry and
   feature details.
5. Open the dashboard at http://localhost:3000/quotes to see the stored quote, filter by status and
   change a quote's status.

## Example quote output

`GET /api/quotes/{id}` for the sample gear at quantity 10 (trimmed):

```json
{
  "file_name": "vendra-gear.STEP",
  "quantity": 10,
  "material": "6061 Aluminum",
  "status": "quoted",
  "geometry": {
    "bounding_box_mm": { "length": 23.368, "width": 22.561, "height": 12.319 },
    "volume_cm3": 1.9522,
    "surface_area_cm2": 14.212,
    "features": { "face_count": 99, "edge_count": 284, "holes_detected": 1, "setups": 2, "thin_wall_count": 1 }
  },
  "cost_breakdown": {
    "pricing_version": "v2-draft",
    "material": { "stock_volume_cm3": 15.366, "computed_cost_order": 2.07, "minimum_applied": true, "cost_order": 10.0, "cost_unit": 1.0 },
    "machine": { "cycle_minutes": 16.49, "thin_wall_count": 1, "mrr_cm3_per_min": 46.25, "cost_unit": 27.48 },
    "setup": { "setups": 2, "setup_hours": 1.56, "cost_unit": 15.6 },
    "total_cost_per_unit": 44.08,
    "total_order_cost": 440.79
  },
  "lead_time_days": 6
}
```

Per unit: $1.00 material + $27.48 machine + $15.60 setup = $44.08. Order total:
$44.08 x 10 = $440.79 (the API rounds unrounded totals, so this can differ by a cent from
multiplying the rounded unit price).

Sample gear at other quantities: qty 1 is $193.44 each, qty 100 is $29.25 each.

## API

Create a quote. It returns `202` immediately with status `queued`:

```bash
curl -F file=@samples/vendra-gear.STEP -F quantity=10 http://localhost:8000/api/quotes
```

Poll until `status` is `quoted` (or `failed`, with an `error`), about a second for the gear:

```bash
curl http://localhost:8000/api/quotes/<id>
```

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/quotes` | Upload `file` (.step/.stp) and `quantity` (1-10,000). 202 + queued quote |
| `GET` | `/api/quotes` | List, newest first. `status`, `limit` (1-100, default 20), `skip`. Returns `{items, total, limit, skip}` |
| `GET` | `/api/quotes/{id}` | Full quote: geometry, cost breakdown, lead time, or the error |
| `PATCH` | `/api/quotes/{id}/status` | `{"status": "reviewed"}` or `"archived"` (see allowed moves below) |
| `GET` | `/api/health` | `{"ok": true}` |

Statuses: `queued` → `processing` → `quoted` or `failed`; a reviewer can then set `reviewed` (from
`quoted`) or `archived` (from `quoted`, `reviewed`, `failed`). Anything else is a 422.

Every error has the same shape: `{ "error": { "code", "message" } }`. Interactive docs:
http://localhost:8000/docs (dev only).

## Assumptions

- One part per file. Several solids are merged into one result with a warning.
- 3-axis machining on a Haas-class machine, one machine dedicated to the order.
- Material is 6061 aluminum at 2.7 g/cm3 and $5.00/kg; machine rate is $100/hour, fully loaded (no
  separate margin).
- Material is priced on **stock volume**, not part volume, because a shop buys and cuts raw stock, so
  the removed material is paid for.
- Stock allowance: **3 mm per side** added to the bounding box.
- Minimum material: **$10 per order** (not per part) covers minimum stock purchases, saw cuts and
  handling. It is shared across the order, so it only matters for small orders.
- Price per unit is `material + machine + setup` (full equations in `REPORT.md`):

  ```
  material_order = max(stock_mass_kg x $5.00 x quantity, $10.00)
  machine        = (roughing_min + hole_min + edge_min) / 60 x $100
  setup          = (programming_hours + fixturing_hours) x $100 / quantity
  ```

- **Setup and CAM programming are a one-time cost per order, amortized across the units.** This is the
  only quantity effect: per-part machine time and material do not change, so the unit price falls as
  volume grows and the order total still rises. There is no separate quantity discount.
- **Roughing rate (MRR, cm3 of metal cut per minute)** starts at **50** (assumption) and thin walls lower
  it linearly to **20**: `MRR = 50 - (50 - 20) x min(thin walls, 8) / 8`. Thin walls flex under the
  cutter, so the shop cuts lighter and slower. The 50, 20 and 8 are assumptions, not measured shop data.
- **Thin walls** are walls less than **3 mm** thick (assumption). The geometry engine counts them and
  stores `thin_wall_count`.
- **Holes** cost a flat 2 min each (assumption); depth is not modeled.
- **Edge time** is `edge count x 0.05 min` (3 s per edge), an assumption: the machine slows and
  re-accelerates where the tool path changes direction, so more edges add time. It is not measured, and
  the edge count includes the seam lines CAD adds to cylinders.
- **Setup hours** are `programming (0.10 + 0.19 x log2(faces)) + 0.10 x setups`. Loading and unloading
  is part of the fixturing hours, so there is no separate handling term. The 0.19 is the one fitted
  number (see Known limitations); the other two are assumptions.
- The surface-area-to-volume ratio is not used in the price.
- The material (density, price, machine rate) comes from `backend/geometry/materials.py`, which holds
  one entry, 6061 aluminum. `--material` on the geometry CLI picks it.
- Lead time is `5 + ceil(machine days) + complexity buffer`, in whole business days, where machine
  days = machine hours / 8 and the buffer is `ceil(machine days x 0.5 x min(faces / 100, 1))`.
  Both rates are assumptions (see `PricingConfig`).
- **No finish assumed:** parts are priced as machined, with no finishing pass, so surface area does not
  drive cost. Standard tolerance; no threads, coatings or inspection reports.
- Quotes are processed asynchronously by a worker, so the API replies `202` and the client polls.
- **Job queue tradeoff:** the queue is the MongoDB `quotes` collection, which the worker polls about once
  a second. A dedicated queue (e.g. Bull with Redis) was rejected: it needs Redis and a Node process,
  FastAPI cannot enqueue Bull jobs natively, and quote status would be split between Redis and Mongo.
  Mongo needs no extra infrastructure and keeps one source of truth, at the cost of polling latency.

The formulas and the reasoning for each are in `REPORT.md`; decisions and alternatives are in
`DECISIONS.md`.

## Known limitations

- **No complexity score.** The lead-time complexity
  buffer uses face count only, so it ignores setups and thin walls. The price is driven by removed
  volume, hole count, edge count, thin-wall count, setup count and face count. The
  surface-area-to-volume ratio is measured but does not change the price.
- **Pricing is fitted to one data point.** `pricing_version` is `v2-draft`. One setup constant
  (`programming_hours_per_log2_face` = 0.19) was fitted so the sample gear at qty 1 ($193.44) lands in
  the competitors' roughly $190-$196; every other constant is an assumption. There are no competitor
  numbers for qty 10 or 100, so those prices are unchecked and the split between setup and cutting
  time is unverified. The bracket sample prices at about $168 at qty 1.
- **Hole and edge time are rough.** Holes ignore depth, and the edge time uses a count (which includes
  CAD seam lines) instead of total edge length.
- **Heuristic feature detection.** Holes and thin walls (under 3 mm) are counted; pockets, slots,
  threads and undercuts are not detected. Two same-size blind holes drilled from opposite faces along
  one axis count as one. The thin-wall count samples points on each face, so it can change with the
  sampling density (the gear is 1 at most densities and 2 at one).
- **Setup count is approximate.** Angled faces and angled holes are ignored.
- **Stock is a plain block** with a fixed allowance; standard bar and plate sizes are not modeled.
- **One lead time**, not expedite/standard/economy tiers.
- **The worker polls the database** (about once a second) instead of being notified of new jobs. A
  future improvement is an async job pool (see `REPORT.md`, Future improvements).
- **No authentication**, payments or multi-user permissions (out of scope).

## Tests

```bash
uv run python -m pytest     # MongoDB tests are skipped unless `docker compose up -d mongo` is running
uv run ruff check .
cd web && npm run build && npm run lint
```
