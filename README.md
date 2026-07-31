# Parts — Multi-Location Dealership Parts AI

**Repository:** https://github.com/seanebones-lang/parts  
**Owner:** NextEleven LLC  
**Package:** `parrts` v0.5.0  
**License:** Proprietary — NextEleven LLC (see `LICENSE`)

---

## What this is

**Parts** is an AI-assisted **multi-location dealership parts** platform:

1. **`parrts` core** — offline-capable hybrid RAG (dense + BM25 + RRF), traffic-light stock policy, CLI & thin API  
2. **Enterprise backend** — FastAPI, 15 `/api/v1` route groups, LangGraph specialist agents, optional Postgres/pgvector  
3. **Frontend** — Next.js 15 parts search UI with live API + mock fallback  
4. **Ops** — Dev + **prod** Compose, hard-fail CI, eval harness, pgvector seed script  

Natural language example:

```bash
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
```

Returns ranked SKUs across locations with **green / yellow / red** confidence for human-in-the-loop.

---

## Honesty table (read this first)

| Layer | Path | What works today |
|-------|------|------------------|
| **Retrieval SoT** | `src/parrts/` | Hybrid RAG, traffic-light, offline tests, eval **12/12 hit@5** |
| **Enterprise API** | `backend/` | Boots without Postgres for `/`, `/health`, `/query`, `/metrics`; **15/15** `/api/v1`; prod secret guard; JWT on writes when `AUTH_MODE=production` |
| **Agents** | `backend/app/agents/` | LangGraph specialists; soft-fail offline; parts path uses `parrts` |
| **Frontend** | `frontend/` | Typed client, traffic-light badge, **`npm run build` green** |
| **DMS Core** | `src/parrts/dms/` + `/api/v1/dms` | Offline SQLite ops: inventory, customers, orders + OEM feed adapters |
| **OEM feed** | adapters synthetic/file/http | Live HTTP when `OEM_FEED_URL` set — no invented OEM credentials |
| **Legacy demos** | `archive/legacy-pitch/` | Streamlit / pitch walkthroughs — **not** the modern SoT |
| **Payments / shipping** | services | **Mock** unless Stripe / EasyPost keys present |
| **Live LLM** | optional | Needs `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` |

Older marketing copy that claims full production SLA for 13 agents, always-live supplier scraping, or guaranteed ROI is **aspirational**. Sell and demo against **measured** paths below.

**Positioning:** pilot / design-partner ready core + API shell — not multi-tenant GA with live pay/ship.

---

## Quick start (no API keys)

### Dealership room demo (recommended)

```bash
git clone https://github.com/seanebones-lang/parts.git
cd parts
./scripts/demo_up.sh          # API :8000 + UI :3000 + ingest
# open http://127.0.0.1:3000/parts
./scripts/demo_smoke.sh       # optional health check
./scripts/demo_down.sh        # stop
```

Pitch script: [`docs/DEALERSHIP_PITCH.md`](docs/DEALERSHIP_PITCH.md)

### CLI only

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m parrts ingest --force
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
python -m parrts query "oil filter Toyota Camry" --no-llm --expand-parent
pytest -q
python scripts/eval_retrieval.py
```

### Backend smoke (enterprise surface)

```bash
pip install -e ".[dev,api]"
pip install -r backend/requirements.txt
PYTHONPATH=backend:src python scripts/verify_boot.py
# uvicorn: PYTHONPATH=backend:src uvicorn main:app --app-dir backend --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run type-check
npm run build    # production build required in CI
npm run dev      # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` if the API is local.

### Docker

```bash
# Dev profiles (reload / bind mounts)
docker compose --profile core up -d      # postgres (pgvector image) + redis
docker compose --profile api up -d       # + backend
docker compose --profile full up -d      # + frontend + workers

# Production-style (no reload; required secrets)
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
docker compose -f docker-compose.prod.yml up -d --build
```

Profiles (dev file): `core` | `pgvector` | `api` | `full` | `obs` (Flower).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)     CLI `parrts`     archive legacy UI   │
└────────────┬──────────────────┬───────────────┬─────────────┘
             │                  │               │
             ▼                  ▼               ▼
┌──────────────────── Thin /query + FastAPI main ─────────────┐
│  /  /health  /query  /metrics  /api/v1/*                      │
└────────────┬───────────────────────────────┬────────────────┘
             │                               │
             ▼                               ▼
┌────────────────────────┐     ┌─────────────────────────────┐
│ parrts core (SoT)      │     │ LangGraph specialists         │
│ hybrid dense+BM25 RRF  │◄────│ parts, CS, inventory, pricing │
│ traffic-light policy   │     │ payment, shipping, supplier…  │
│ HashingEmbedder default│     │ soft-fail if DB/LLM down      │
└────────────────────────┘     └─────────────────────────────┘
             │
             ▼ optional
      Postgres + pgvector + Redis + Celery
```

---

## CLI reference

| Command | Purpose |
|---------|---------|
| `parrts ingest [--force]` | Build inventory + indexes under `.parrts/` |
| `parrts query "…" [--no-llm] [-k 5] [--location NAME] [--rerank] [--expand-parent]` | JSON retrieval |
| `parrts status` | Index / inventory summary |

Embedder: `PARRTS_EMBEDDER=hash|st|bge|openai|auto` or `--embedder`.

---

## Environment (high signal)

Copy `.env.example` → `.env`.

| Variable | Default | Meaning |
|----------|---------|---------|
| `ENVIRONMENT` | `development` | `production` enables secret guard |
| `SECRET_KEY` | placeholder | **Required strong value** when production / `AUTH_MODE=production` |
| `AUTH_MODE` | `demo` | `demo` = JWT optional on writes; `production` = JWT required |
| `DEBUG` | `true` | Must be `false` in production runtime |
| `PGVECTOR_ENABLED` | `false` | Opt-in SQL vector path |
| `VECTOR_BACKEND` | `auto` | `auto` \| `parrts` \| `pgvector` |
| `PARRTS_EMBEDDER` | `hash` | Offline-safe default |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | empty | Optional LLM synthesis |
| `STRIPE_*` / `EASYPOST_API_KEY` | empty | Live pay/ship only if set |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Frontend API base |

---

## Testing & quality

```bash
pytest -q
ruff check src tests
PYTHONPATH=backend:src pytest -q tests/test_backend_boot.py
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/eval_retrieval.py --dataset default -k 5
cd frontend && npm run type-check && npm run build
```

**Last measured (Wave 11):** 67 passed, 2 skipped; eval 12/12 @ hit@5; FE production build green; prod secret guard rejects insecure keys.

CI (GitHub Actions): Python 3.11/3.12 core (hard ruff + eval), backend-smoke, frontend type-check **+ build**, compose config (dev + prod).

---

## Repo map

```
src/parrts/           # hybrid RAG package (SoT) v0.5.0
backend/              # FastAPI + agents + services
frontend/             # Next.js UI
scripts/              # eval_retrieval, verify_boot, seed_pgvector
tests/                # offline unit + boot + auth + workflow
docs/                 # CTO_BACKLOG, AGENTS, ROADMAP
archive/legacy-pitch/ # historical demos / pitch docs
docker-compose.yml    # dev profiles
docker-compose.prod.yml
```

**5-minute demo script:** [`docs/DEMO_WALKTHROUGH.md`](docs/DEMO_WALKTHROUGH.md)  
Agent ownership: [`docs/AGENTS.md`](docs/AGENTS.md)  
Execution history: [`docs/CTO_BACKLOG.md`](docs/CTO_BACKLOG.md)

---

## Security & licensing

- **Proprietary.** Not open source. See `LICENSE` (NextEleven LLC).  
- Production boot **fails** if `SECRET_KEY` is a known default or `DEBUG=true` while `ENVIRONMENT`/`AUTH_MODE` is production.  
- Mutating `/api/v1` routes use `require_user_if_production`.  
- Demo mode is for controlled demos only.  
- Do not bind the API to public networks without TLS, auth, and network controls.

---

## Support / commercial

**NextEleven LLC** — Frisco, Texas  
Product & sales materials: local Desktop folder `parts docs` when present.  
Engineering ship target: https://github.com/seanebones-lang/parts  

---

## Changelog snapshot

- **v0.5.0 (Wave 11)** — CI hard gates, FE production build (Recharts SSR fix), prod secret guard, write-route JWT wiring, `docker-compose.prod.yml`, proprietary license metadata, legacy pitch archived  
- **v0.4.x** — hybrid core, 15/15 API boot, LangGraph specialists, pgvector seed, AUTH_MODE demo/prod deps  
