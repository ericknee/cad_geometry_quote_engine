# Vendra Quoting Engine

Upload a `.step` file, pick a quantity, get an explainable CNC quote for 6061 aluminum. See
`Vendra_Quoting_Engine_PRD.md` for requirements.

> Skeleton only. Install/run, example output, assumptions and limitations are filled in as features land.

## Run locally

```bash
cp .env.example .env
docker compose up -d mongo
uv sync && uv run python -m uvicorn api.main:app --reload --app-dir backend   # http://localhost:8000/api/health
cd web && npm install && npm run dev                                         # http://localhost:3000
```

Or the whole stack: `docker compose up --build`.
