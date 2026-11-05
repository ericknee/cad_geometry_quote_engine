# Vendra Quoting Engine

Upload a `.step` file, pick a quantity, get an explainable CNC quote for 6061 aluminum. See
`Vendra_Quoting_Engine_PRD.md` for requirements and `DECISIONS.md` for why things are built this way.

> Work in progress: the backend (geometry, pricing, API, worker) works; the web pages are
> placeholders. Install notes, assumptions and limitations are filled in as features land.

## Run locally

```bash
cp .env.example .env
docker compose up -d mongo
uv sync
uv run python -m uvicorn api.main:app --reload --app-dir backend   # API: http://localhost:8000/api/health
uv run python -m api.worker                                        # worker: second terminal
cd web && npm install && npm run dev                               # web: http://localhost:3000
```

The **worker must be running** next to the API: the API only queues a quote, the worker analyzes the
file and prices it. Without a worker, quotes stay `queued`.

Or the whole stack: `docker compose up --build` (mongo, api, worker, web).

## Geometry CLI (no server needed)

```bash
uv run python backend/analyze_geometry.py samples/vendra-gear.STEP
```

## API example

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

## Tests

```bash
uv run python -m pytest     # MongoDB tests are skipped unless `docker compose up -d mongo` is running
uv run ruff check .
```
