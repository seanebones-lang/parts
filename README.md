# Parts — Multi-Location Dealership Parts AI

**Repository:** https://github.com/seanebones-lang/parts  
**Owner:** NextEleven LLC  
**Package:** `parrts` v0.4.2  
**License:** Proprietary — NextEleven LLC (see `LICENSE`)

---

## What this is

**Parts** is an AI-assisted **multi-location dealership parts** platform:

1. **`parrts` core** — offline-capable hybrid RAG (dense + BM25 + RRF), traffic-light stock policy, CLI & thin API  
2. **Enterprise backend** — FastAPI, 15 `/api/v1` route groups, LangGraph specialist agents, optional Postgres/pgvector  
3. **Frontend** — Next.js 15 parts search UI with live API + mock fallback  
4. **Ops** — Docker Compose profiles, CI matrix, eval harness, pgvector seed script  

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
| **Enterprise API** | `backend/` | Boots without Postgres for `/`, `/health`, `/query`, `/metrics`; **15/15** `/api/v1` modules load |
| **Agents** | `backend/app/agents/` | LangGraph graph with specialists; soft-fail offline; parts path uses `parrts` |
| **Frontend** | `frontend/` | Typed client, traffic-light badge, TypeScript clean |
| **Legacy demos** | root `*.py`, `demo/` | Streamlit / pitch walkthroughs — not the modern SoT |
| **Payments / shipping** | services | **Mock** unless Stripe / EasyPost keys present |
| **Live LLM** | optional | Needs `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` |

Older marketing copy that claims full production SLA for 13 agents, always-live supplier scraping, or guaranteed ROI is **aspirational**. Sell and demo against **measured** paths below.

---

## Quick start (no API keys)

```bash
git clone https://github.com/seanebones-lang/parts.git
cd parts
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
# from backend/ with PYTHONPATH=backend:src
# uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci   # or npm install
npm run type-check
npm run dev   # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` if the API is local.

### Docker (optional)

```bash
# Requires Docker Desktop running
docker compose --profile core up -d      # postgres (pgvector image) + redis
docker compose --profile api up -d       # + backend
docker compose --profile full up -d      # + frontend + workers
PGVECTOR_ENABLED=true python scripts/seed_pgvector.py
```

Profiles: `core` | `pgvector` | `api` | `full` | `obs` (Flower).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)     Streamlit UI     CLI `parrts`         │
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
| `AUTH_MODE` | `demo` | `demo` = JWT optional on wired writes; `production` = JWT required |
| `PGVECTOR_ENABLED` | `false` | Opt-in SQL vector path |
| `VECTOR_BACKEND` | `auto` | `auto` \| `parrts` \| `pgvector` |
| `PARRTS_EMBEDDER` | `hash` | Offline-safe default |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | empty | Optional LLM synthesis |
| `STRIPE_*` / `EASYPOST_API_KEY` | empty | Live pay/ship only if set |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Frontend API base |

---

## Testing & quality

```bash
pytest -q                                          # core + backend when deps present
PYTHONPATH=backend:src pytest -q tests/test_backend_boot.py
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/eval_retrieval.py --dataset default -k 5
python scripts/eval_retrieval.py --dataset extended -k 5
# Optional heavy:
# PARRTS_TEST_ST=1 pytest -q tests/test_optional_st_embedder.py
```

**Last measured (2026-07-31):** 59 passed, 2 skipped; eval 12/12 @ hit@5; FE `tsc` clean.

CI (GitHub Actions): Python 3.11/3.12 core, backend-smoke job, frontend type-check, compose config.

---

## Repo map

```
src/parrts/           # hybrid RAG package (SoT)
backend/              # FastAPI + agents + services
frontend/             # Next.js UI
scripts/              # eval_retrieval, verify_boot, seed_pgvector
tests/                # offline unit + boot + workflow + mocks
docs/                 # CTO_BACKLOG, AGENTS, ROADMAP
demo/ + root *.py     # legacy pitch demos
docker-compose.yml    # profiles core/api/full/pgvector/obs
```

Agent ownership for multi-agent development: [`docs/AGENTS.md`](docs/AGENTS.md)  
Execution history: [`docs/CTO_BACKLOG.md`](docs/CTO_BACKLOG.md)

---

## Security & licensing

- **Proprietary.** Not open source. See `LICENSE` (NextEleven LLC).  
- Do not bind the API to `0.0.0.0` in production without auth and network controls.  
- Demo mode is for controlled demos only — use `AUTH_MODE=production` with JWT for real deployments.

---

## Support / commercial

**NextEleven LLC** — Frisco, Texas  
Product & sales materials: local Desktop folder `parts docs` (sales packet, LinkedIn, email, dealership info).  
Engineering ship target: https://github.com/seanebones-lang/parts  

---

## Changelog snapshot

| Version | Highlights |
|---------|------------|
| **0.4.2** | LangGraph specialists expand; Pydantic v2 schemas |
| **0.4.1** | Full `/api/v1` 15/15; verify_boot |
| **0.4.0** | Parent expand, eval metrics, compose profiles, `/metrics` |
| **0.3.x** | Modern core hybrid RAG + backend boot honesty |

---

*This README replaces aspirational monologues with a dual-stack truth: ship the core, grow the enterprise surface with keys and Docker when ready.*
