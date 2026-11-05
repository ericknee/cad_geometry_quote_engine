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

## 2. Quote calculation (`backend/pricing`) — Built

- **Pure package, input is `GeometryResult`** — Built
  - No web or DB. `price(geometry, quantity, config)`; all constants in one config object with a `pricing_version`.
  - Alternative: a separate small input type (more decoupled, but a second type and a mapping layer).
  - Note: the owner chose the direct type because it is simpler and fully typed.
- **Config is a frozen Pydantic model** — Built
  - One object holds every constant; it validates the discount and complexity-band tables (start at the right value, ascend, rates between 0 and 1).
  - Alternative: a plain dataclass (lighter, no validation).
  - Note: chosen by the owner for consistency with the geometry result types.
- **Cost breakdown is nested by group, with `cost_order` on every group** — Built
  - Groups: material, machine, setup, discount, plus totals. The backend supplies both the per-unit and per-order columns, so the frontend only displays them and all math is in one tested place.
  - Alternative: only setup carries `cost_order` and the frontend multiplies (smaller data, but math in two places and possible mismatches).
  - Note: the owner approved the field names and chose per-order values on every group.
- **Rounding: compute unrounded, round once at output** — Built
  - A displayed line can differ from its displayed total by a cent, and a rounded unit value times quantity can differ from the order value by up to half a cent per part. To be noted in the README.
  - Alternative: round each line and add the rounded lines (columns add up exactly, but deviates from the PRD rule).
  - Note: the owner chose sum-then-round.
- **Material priced on stock volume, not part volume** — Built
  - Why: shops buy and cut raw stock, so removed material is paid for too. The challenge requires this to be explained in the README and report.
  - Origin: PRD.
- **$10 minimum material charge** — Built
  - The gear's computed material cost is about $0.20; the minimum reflects minimum stock purchases and saw cuts. The breakdown reports the computed value and whether the minimum applied.
  - Origin: PRD.
- **Quantity discount applied only at totals** — Built
  - `discount_unit = machine_cost_unit × rate`. Machine minutes are never reduced, so lead time uses full hours. The discount is its own line.
  - Tiers: 1-5 0%, 6-20 10%, 21-100 20%, 101+ 30%. Qty 100 is in the 20% tier (the source overlapped at 100).
  - Origin: PRD.
- **Starting constants (placeholders, tuned later)** — Built
  - Roughing 1.0 cm³/min, finishing 1.0 cm²/min, 2 min per hole, 3 min handling, $100/h.
  - Gear result: $204.38 at qty 1, $72.94 at qty 10, $54.90 at qty 100 (competitors charge ~$190-196 at qty 1; their qty 10 and 100 prices are not available). Not fitted to data.
  - Note: the owner accepted these as a starting point and chose to keep the finishing rate at 1.0 for now.
- **Setup hours scale with estimated setups** — Built
  - `setup_hours = base × (1 + 0.25 × (setups − 1))`; base chosen at calibration so the gear (2 setups) is about 1.4 h.
  - Note: the owner accepted this formula for now.
- **Complexity placeholder 1.0** — Built
  - Pricing reads `features.complexity_score` and falls back to a config default of 1.0, so the real score drops in later with no pricing change.
  - Note: the owner chose this over designing the score now, so the endpoints are not delayed.
- **Calibration on charged prices** — Decided
  - Competitor 1 shows ~23.8% off a struck-through list price. Calibration uses what the customer pays ($196.43, $189.41), not list. Qty 10 and 100 data are still missing.
  - Origin: PRD.

## 3. Lead time — Built

- **Business days = 5 + ceil(machine hours / 8) + complexity buffer (0/1/2)** — Built
  - Separate result object (`LeadTime`), kept apart from the cost breakdown. Gear: 6 days at qty 1 and 10, 12 days at qty 100.
  - Machine hours = setup hours + undiscounted cycle hours × quantity.
  - The complexity buffer depends on the complexity score, so it is 0 until that exists.
  - Origin: PRD.

## 4. API and job queue (`backend/api`, worker) — Built

- **FastAPI, layered router → service → repository** — Built
  - Only repositories touch collections. Error shape `{ "error": { "code", "message" } }`.
  - Origin: PRD and project conventions.
- **Async job queue with a separate worker process** — Built
  - `POST /quotes` returns 202 and a `queued` quote; a worker claims jobs atomically from Mongo and runs geometry and pricing.
  - Alternatives: `asyncio.to_thread` (~15-20 lines, keeps the PRD's 201 response); process pool (~45-60 lines); job queue (~350-500 lines).
  - Note: the owner chose the queue after comparing these options. A separate worker means a kernel crash only stops the worker, not the API.
  - PRD deviation: the PRD specifies 201 with the full quote and lists async jobs as a stretch goal.
- **Upfront validation returns 422; analysis failures are stored** — Built
  - Wrong extension, oversize file, bad quantity: 422, nothing saved. Corrupt STEP or no solids: the record is kept as `failed` with error code and message.
  - Note: with a queue, analysis failures are only known after the 202, so they must be stored on the quote.
- **Statuses: `queued` → `processing` → `quoted` / `failed`, then `reviewed`, `archived`** — Built
  - Note: the owner chose to rename the PRD's `new` to `queued` and add `processing` and `failed`, so each job state is explicit.
  - PRD deviation: the PRD has `new`, `quoted`, `reviewed`, `archived`.
- **Client polls `GET /quotes/{id}` (~1 s)** — Built
  - Alternatives: server-sent events (the server would still poll Mongo because the worker is a separate process, so no real speed gain, plus a proxy buffering risk); a dedicated `/job` endpoint (extra endpoint).
  - Note: the owner chose polling after comparing it with SSE.
- **List returns `{items, total, limit, skip}`** — Built
  - Note: the owner chose this because the dashboard needs a total for paging.
  - PRD deviation: the PRD shows a bare array.
- **Allowed status changes by a reviewer: `quoted` → `reviewed`, any finished quote → `archived`** — Built
  - `queued`, `processing` and `failed` are set only by the system; a quote mid-job cannot be archived. Everything else returns 422. A `failed` quote may be archived so it can be cleared from the dashboard.
  - Alternatives: also allow un-archiving and `reviewed` → `quoted`; or allow any user-settable status from any state (simplest, but a failed quote could be marked reviewed).
  - Note: the owner chose the stricter rule, which keeps the PRD lifecycle meaningful.
- **Upload checks: extension, size, empty, STEP header** — Built
  - `.step`/`.stp` (any case), at most `MAX_UPLOAD_MB`, not empty, and the first line must be `ISO-10303-21` (the header every STEP file has). Each failure is a 422 `INVALID_FILE` and nothing is saved.
  - The file is streamed to disk in 1 MB chunks and hashed on the way, so a 50 MB file is never held in memory and an oversize upload stops early.
  - Stored as `<UPLOAD_DIR>/<random id>.step`. The client's name is only kept for display (path parts and control characters removed), so a hostile name cannot choose where the file goes.
  - Why the header check: a renamed `.txt` fails in milliseconds with a clear message instead of after a queue wait. It does not prove the file is valid; the geometry engine still decides that.
  - Alternative: extension only (simpler, but the user waits for the worker to learn the file is not STEP).
- **Duplicate uploads create a new quote each time** — Built
  - The SHA-256 is stored, so caching analysis by hash stays possible later (a PRD stretch item). Not done now: it adds a cache-invalidation rule for little gain at this scale.
- **Quantity range is checked in the service, not by request validation** — Built
  - 1 to 10,000 (PRD). A bad number returns `INVALID_QUANTITY`; only a non-number returns the generic `VALIDATION_ERROR`. Keeps the rule in one place and gives the UI a specific code.
- **One error shape for every failure** — Built
  - Handlers turn domain errors, request-validation errors and unknown routes into `{ "error": { "code", "message" } }`. Validation errors report only the first problem, as `field: reason`.
- **Startup checks: MongoDB ping, absolute upload folder** — Built
  - The API pings MongoDB when it starts, so a wrong connection string stops the boot with a clear message (5 s limit) instead of failing on the first request. `/api/health` stays free of database calls.
  - `UPLOAD_DIR` is resolved to an absolute path and created at startup. A relative path would depend on where each process was started, and the API and worker could look in different places.
  - Known gap: if the geometry engine rejects a file, its message names the stored random filename, not the user's. Cosmetic; to fix later by passing the display name to the engine.
- **One response model with optional result fields** — Built
  - `QuoteDetail` has `geometry`, `cost_breakdown`, `lead_time` as `None` until the quote is priced, and `error` only when it failed. The dashboard row (`QuoteSummary`) is built from it, so the two cannot drift.
  - Alternative: a separate model per status (stricter, but more types and a harder API schema).
  - Note: the owner chose the single model for simplicity.
  - PRD deviation: the geometry result is stored whole under `geometry`, so the PRD's separate `features` object is `geometry.features`.
- **Status changes are compare-and-set** — Built
  - The update only applies if the quote still has the status that was read, so a reviewer and the worker cannot overwrite each other. A lost race returns 409 (`STATUS_CONFLICT`).
- **Atomic job claim** — Built
  - The worker takes the quote that has waited longest (by `updated_at`) and marks it `processing` in one database operation, so two workers can never get the same job. Verified with 25 simultaneous claims against 10 quotes.
  - Ordering by `updated_at` (equal to `created_at` for a new quote) sends a quote released for retry to the back of the queue, so a file that keeps crashing cannot block the ones behind it. Cost: strict first-in-first-out is lost for retried quotes.
  - Results and retries are written only under the claim that made them (`attempts` must still match), so a stalled worker cannot overwrite or re-queue a job another worker has since claimed. A refused write is logged.
- **Each analysis runs in a child process** — Built
  - The worker runs the existing CLI (`python -m geometry <file>`) per job. Exit code 0 is a result, 1 is a normal error (bad file); anything else, an unreadable output or a timeout (120 s) counts as a crash.
  - Why: a hard crash in the C++ kernel cannot be caught in Python and would kill the worker. In a child process only that job is affected.
  - Alternatives: run in the worker itself (simpler, but one bad file could crash-loop the worker and block the queue); a process pool (needs pickling and pool rebuilding after a crash).
  - Cost: about 1 s of extra start-up per job (the gear takes under 1 s in total).
  - Note: the owner chose crash isolation for this reason.
- **Crashed analyses are retried, up to 3 retries** — Built
  - A counter (`attempts`) goes up each time a job is claimed. A crash puts the job back in the queue while retries remain; after the first try plus 3 retries (4 attempts) the quote is `failed` with `ANALYSIS_CRASHED`.
  - A bad file (normal error) is not retried, since it would fail the same way every time. Unexpected errors fail the quote too, so nothing stays stuck in `processing`.
  - Why retry at all: a crash can be a one-off (for example, running out of memory on a busy machine) and cannot be told apart from a bad file.
  - Note: the owner asked for the counter with a maximum of 3 retries.
- **Stale-job recovery** — Built
  - A job stuck in `processing` for more than 5 minutes (worker died) is recovered by the same counter: re-queued if attempts remain, otherwise `failed` (`JOB_ABANDONED`), so a job that keeps killing its worker cannot loop forever. Checked on worker start and every 60 s.
  - The 5-minute limit is above the 120 s analysis timeout so a live job is never taken away.
- **Worker loop survives database errors, then exits** — Built
  - An error in one loop pass (e.g. MongoDB unreachable) is logged and retried after 5, 10, then 20 s. A 4th failure in a row ends the process; any successful pass resets the count.
  - Why: short outages need no restart, while a permanent fault (wrong URI, bug) becomes visible instead of looping silently. Docker's `restart: unless-stopped` restarts the worker.
  - Alternatives: crash on the first error (no help for local runs); retry forever (hides permanent faults).
  - Note: the owner chose exponential backoff with a maximum of 3 retries.

## 5. Database (MongoDB)

- **MongoDB via PyMongo's async client (`AsyncMongoClient`), not Motor** — Built
  - One `quotes` collection, indexes created at startup, no migrations.
  - Origin: PRD preference for MongoDB.
- **Indexes: `created_at` descending, and `(status, created_at)`** — Built
  - The compound index also serves plain status filters and the worker's "oldest queued" lookup, so a separate `status` index (listed in the PRD) is not needed.
  - Created at startup; no migrations.
- **Repository tests run against a real MongoDB and skip when it is not running** — Built
  - Why: the atomic job claim can only be proven on the real database. Start it with `docker compose up -d mongo`.
  - Alternatives: `mongomock` (runs anywhere, but a fake cannot prove atomicity); both.
  - Note: chosen by the owner.
- **Uploads stored outside any web root; the database stores path and SHA-256** — Built
  - Origin: PRD security requirement.

## 6. Frontend — not started

- Stack from the PRD: Next.js (App Router), TypeScript, Tailwind.
- The result page will poll while a quote is `queued` or `processing` and show the error for `failed`.

## 7. Process

- **Every technical decision is made with the owner, with plain-language explanations.**
  - Why: the owner has no CAD or manufacturing background and must defend each decision.
- **Claims are verified against the sample files before they are relied on** (see the setup rule above).
