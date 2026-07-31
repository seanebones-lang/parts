# Backend — Dealership Parts API

**Entry:** `main.py` (FastAPI)  
**Routes:** `/`, `/health`, `/query`, `/metrics`, `/api/v1/*`  
**Core RAG:** `src/parrts` (mounted at `/src` in Docker; `PYTHONPATH=/app:/src`)

## Run locally

```bash
# from monorepo root
pip install -e ".[dev,api]"
pip install -r backend/requirements.txt
PYTHONPATH=backend:src python scripts/verify_boot.py
PYTHONPATH=backend:src uvicorn main:app --app-dir backend --reload --port 8000
```

## Layout

```
backend/
  main.py           # app entry
  app/              # api, agents, models, services
  init.sql          # optional Postgres bootstrap
  requirements.txt
  Dockerfile        # build from monorepo root
```

Legacy pitch APIs live under `archive/legacy-pitch/backend-demos/` — not used by production entry.
