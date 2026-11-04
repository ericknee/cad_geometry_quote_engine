# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Vendra mini quoting engine: upload a `.step` file and a quantity, get an explainable CNC quote
(6061 aluminum), store it in MongoDB, manage it in a dashboard. Full requirements are in
`Vendra_Quoting_Engine_PRD.md`. Layout and conventions follow the sibling `hangry` project.

**Status: bare skeleton.** The quotes endpoints return 501, the web pages are placeholders, and the
`geometry/` and `pricing/` packages do not exist yet.

## Layout

- `backend/api` — FastAPI service (`api.*`): routers → services → repositories, plus `types/`,
  `errors/`, `utils/`, `db/`, `config.py`, `deps.py`. Files are named `<feature>_<layer>.py`
  (feature: `quotes`).
- `backend/tests` — tests mirror the code (`tests/api/`).
- `web` — Next.js (App Router) + TypeScript + Tailwind. `src/app/` holds thin route files that render
  a component from `src/views/<page>/` (one folder per page). `src/components/` is shared UI only.
  Not named `pages/` because `src/pages` would enable Next's legacy Pages Router.
- `samples` — sample STEP files.

One Python project at the repo root (`pyproject.toml`, one lockfile). **Dependency rule:** when
`backend/geometry` and `backend/pricing` are added they stay pure (no web, no DB); `api` imports
them, never the reverse. Imports inside `api` go one way: router → service → repository.

## Commands

```bash
cp .env.example .env
docker compose up -d mongo          # MongoDB on localhost:27017
uv sync
uv run python -m uvicorn api.main:app --reload --app-dir backend   # API on :8000
cd web && npm install && npm run dev                               # web on :3000
npm install && npm run dev          # (repo root) runs API and web together
```

```bash
uv run python -m pytest             # `uv run pytest` fails on Windows; use python -m
uv run ruff check .                 # lint
uv run ruff format .                # format
cd web && npm run build && npm run lint
docker compose up --build           # whole stack: mongo, api, web
```

## Notes

- The browser calls `/api/*` on the web origin; `web/next.config.ts` rewrites it to `API_URL`
  (default `http://localhost:8000`, a build arg in Docker). No CORS.
- `web/next.config.ts` enables `cacheComponents`: runtime data such as `params` must be read under
  `<Suspense>` (see `app/quotes/[id]/page.tsx`). This Next version differs from older ones; check
  `web/node_modules/next/dist/docs/` before relying on memory.
- MongoDB via PyMongo's async client (`AsyncMongoClient`, not Motor). No migrations: create indexes
  at startup in `api/db/`. Only repositories touch collections.
- Uploaded files live under `UPLOAD_DIR`, outside any web root; the database stores path and hash.
- Error shape: `{ "error": { "code", "message" } }`.
