# Decision Log

One entry per significant decision, grouped by component. Each entry: the decision, alternatives
considered, and why. "Origin" appears only when the decision comes from an external source (the PRD).

Status: **Built** (in the code), **Decided** (agreed, not built yet).

---

## 1. Geometry engine (`backend/geometry`)

- **OpenCascade via `cadquery-ocp`, pinned to `8.0.1.1.0`** — Built
  - Why: exact STEP parsing, mass properties and surface-type inspection. Pinned because OCP 8 renamed several calls.
  - Alternatives: `pythonocc-core`, `cadquery` wrapper.
  - Origin: PRD recommendation.
- **Standalone CLI plus library** — Built
  - `python -m geometry <file>` plus a thin `backend/analyze_geometry.py` wrapper; the API imports the same `analyze_file`.
  - Why: the PRD requires one implementation (FR-G2).
  - Note: confirmed by the owner.
- **Result types are frozen Pydantic models** — Built
  - Why: Pydantic is already a dependency, validates the output shape, and the same types can be reused as API responses. Frozen so results cannot change after creation.
  - Alternatives: dataclasses.
  - Note: the owner rejected "purity" as a reason, so the justification is validation and reuse.
- **Units: trust the kernel's conversion to mm** — Built
  - The source unit is only a label. Verified on the gear sample, which is authored in inches.
  - Alternative: rescale manually (rejected: it would convert twice).
- **Axis-aligned bounding box only** — Built
  - Why: matches the competitor's reported size. An oriented box is a documented future improvement.
  - Note: owner decision.
- **Stock = box + 3 mm per side** — Built
  - Constant in the geometry package, adjustable via `--stock-allowance`. Not rounded to standard bar sizes.
  - Note: the owner confirmed the allowance as an adjustable constant.
- **Multiple solids: merge and warn** — Built
  - One box around all solids, volumes and areas added. Per-solid analysis stays separate (`analyze_solid`).
  - Note: the owner wants a per-solid quote layer to be possible later.
- **Validation** — Built
  - Kernel validity check (`BRepCheck_Analyzer`) rejects open or self-intersecting solids. Zero-size solids are rejected. Unusual sizes (<0.5 mm thick, >2000 mm long) only warn, since they usually mean a wrong unit.
  - The kernel's own stdout messages are silenced so CLI output stays valid JSON. Cost: less kernel detail; our error codes still report the failure.
- **Hole detection rule** — Built
  - Cylinder faces are grouped by axis and radius. A group is a hole if (a) a point just outside the wall lies in material (excludes bosses and hubs) and (b) its arcs sum to at least 270°.
  - Counterbores (coaxial cylinders touching end to end) count as one hole.
  - Why 270°: keeps holes partly cut away by another feature; drops fillets, tooth-root scallops and 180° slot ends.
  - Weakness: the two sample parts give the same result for any threshold between 100° and 360°, so 270° rests on reasoning, not data.
  - Known limit: two same-size blind holes drilled from opposite sides on one axis merge into one.
  - Note: the owner approved the rule after both samples were inspected.
- **Complexity score deferred** — Decided
  - Left as `None` until CNC machining costs are known. Pricing uses a fallback of 1.0 meanwhile.
  - Idea not yet adopted: combine SA:V, face density, holes and removal ratio, clamped to 1.0-3.0. Gear face density (~51/cm³) vs bracket (~0.4) needs a cap or log scale.
  - Note: the owner will define the score once real machining costs are known.
- **Setup estimate (`features.setups`)** — Built
  - Rule: main axis = thinnest direction; +1 for each of its two sides that has a flat face pointing straight out; +1 per other axis that has hole openings; minimum 1. Side walls are free (cut during the outline pass).
  - Results: gear 2 (matches the PRD assumption), bracket 4.
  - Alternatives: always 2; count all face directions; fixed 2 from config.
  - Note: a first rule based on opposing pairs was tested on the samples and gave 1 setup for the gear, so it was replaced. The owner chose this rule over the alternatives.
  - Limits: ignores angled faces and holes; ties for thinnest pick the first axis; the bracket's value is not checked against a real shop.
  - PRD: lists setup estimation under future improvements; this is a simple first version.

## 2. Quote calculation (`backend/pricing`) — Decided, not built

- **Pure package, input is `GeometryResult`** — Decided
  - No web or DB. `price(geometry, quantity, config)`; all constants in one config object with a `pricing_version`.
  - Alternative: a separate small input type (more decoupled, but a second type and a mapping layer).
  - Note: the owner chose the direct type because it is simpler and fully typed.
- **Material priced on stock volume, not part volume** — Decided
  - Why: shops buy and cut raw stock, so removed material is paid for too. The challenge requires this to be explained in the README and report.
  - Origin: PRD.
- **$10 minimum material charge** — Decided
  - The gear's computed material cost is about $0.20; the minimum reflects minimum stock purchases and saw cuts. The breakdown reports the computed value and whether the minimum applied.
  - Origin: PRD.
- **Quantity discount applied only at totals** — Decided
  - `discount_unit = machine_cost_unit × rate`. Machine minutes are never reduced, so lead time uses full hours. The discount is its own line.
  - Tiers: 1-5 0%, 6-20 10%, 21-100 20%, 101+ 30%. Qty 100 is in the 20% tier (the source overlapped at 100).
  - Origin: PRD.
- **Starting constants (placeholders, tuned later)** — Decided
  - Roughing 1.0 cm³/min, finishing 1.0 cm²/min, 2 min per hole, 3 min handling, $100/h.
  - By hand (not run), these give about $203 for the gear at qty 1, inside the $150-240 target. They are not fitted to data.
  - Note: the owner accepted these as a starting point and chose to keep the finishing rate at 1.0 for now.
- **Setup hours scale with estimated setups** — Decided
  - `setup_hours = base × (1 + 0.25 × (setups − 1))`; base chosen at calibration so the gear (2 setups) is about 1.4 h.
  - Note: the owner accepted this formula for now.
- **Complexity placeholder 1.0** — Decided
  - Pricing reads `features.complexity_score` and falls back to a config default of 1.0, so the real score drops in later with no pricing change.
  - Note: the owner chose this over designing the score now, so the endpoints are not delayed.
- **Calibration on charged prices** — Decided
  - Competitor 1 shows ~23.8% off a struck-through list price. Calibration uses what the customer pays ($196.43, $189.41), not list. Qty 10 and 100 data are still missing.
  - Origin: PRD.

## 3. Lead time — Decided, not built

- **Business days = 5 + ceil(machine hours / 8) + complexity buffer (0/1/2)**
  - Machine hours = setup hours + undiscounted cycle hours × quantity.
  - The complexity buffer depends on the complexity score, so it is 0 until that exists.
  - Origin: PRD.

## 4. API and job queue (`backend/api`, worker) — Decided, not built

- **FastAPI, layered router → service → repository** — Built (skeleton)
  - Only repositories touch collections. Error shape `{ "error": { "code", "message" } }`.
  - Origin: PRD and project conventions.
- **Async job queue with a separate worker process** — Decided
  - `POST /quotes` returns 202 and a `queued` quote; a worker claims jobs atomically from Mongo and runs geometry and pricing.
  - Alternatives: `asyncio.to_thread` (~15-20 lines, keeps the PRD's 201 response); process pool (~45-60 lines); job queue (~350-500 lines).
  - Note: the owner chose the queue after comparing these options. A separate worker means a kernel crash only stops the worker, not the API.
  - PRD deviation: the PRD specifies 201 with the full quote and lists async jobs as a stretch goal.
- **Upfront validation returns 422; analysis failures are stored** — Decided
  - Wrong extension, oversize file, bad quantity: 422, nothing saved. Corrupt STEP or no solids: the record is kept as `failed` with error code and message.
  - Note: with a queue, analysis failures are only known after the 202, so they must be stored on the quote.
- **Statuses: `queued` → `processing` → `quoted` / `failed`, then `reviewed`, `archived`** — Decided
  - Note: the owner chose to rename the PRD's `new` to `queued` and add `processing` and `failed`, so each job state is explicit.
  - PRD deviation: the PRD has `new`, `quoted`, `reviewed`, `archived`.
- **Client polls `GET /quotes/{id}` (~1 s)** — Decided
  - Alternatives: server-sent events (the server would still poll Mongo because the worker is a separate process, so no real speed gain, plus a proxy buffering risk); a dedicated `/job` endpoint (extra endpoint).
  - Note: the owner chose polling after comparing it with SSE.
- **List returns `{items, total, limit, skip}`** — Decided
  - Note: the owner chose this because the dashboard needs a total for paging.
  - PRD deviation: the PRD shows a bare array.

## 5. Database (MongoDB)

- **MongoDB via PyMongo's async client (`AsyncMongoClient`), not Motor** — Built (connection only)
  - One `quotes` collection, indexes created at startup, no migrations.
  - Origin: PRD preference for MongoDB.
- **Uploads stored outside any web root; the database stores path and SHA-256** — Decided
  - Origin: PRD security requirement.

## 6. Frontend — not started

- Stack from the PRD: Next.js (App Router), TypeScript, Tailwind.
- The result page will poll while a quote is `queued` or `processing` and show the error for `failed`.

## 7. Process

- **Every technical decision is made with the owner, with plain-language explanations.**
  - Why: the owner has no CAD or manufacturing background and must defend each decision.
- **Claims are verified against the sample files before they are relied on** (see the setup rule above).
