# Parrts-Dist-RAG — CTO Backlog (2026-07-31)

**Root:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Remote (ship target):** `https://github.com/seanebones-lang/parts`  
**Legacy remote:** `https://github.com/seanebones-lang/Parrts-Dist-RAG`  
**Branch:** `main`  
**SoT:** this file. Mark `[x]` only after real execution + verification.

## Truth audit (Wave 0 findings)

| Claim in marketing docs | Reality (pre max-opt) |
|-------------------------|---------|
| LangGraph multi-agent production system | Scaffold; specialists not fully wired |
| pgvector semantic search | Present; filters were fragile |
| Claude 3.5 Sonnet primary | Stale models; sync Anthropic + await bug |
| FastAPI enterprise backend boots | pydantic v1 BaseSettings break; fake health |
| FAISS + LangChain RAG demo | Root keyword mock; LangChain 0.1 freeze |
| Next.js 15 frontend | Invalid radix packages |
| Deps production ready | 2023–early-2024 freeze |
| Test suite | Demo scripts only |

**Max-opt north star:** importable **`parrts` core** shared by CLI, FastAPI, frontend client, and `parts_lookup`.

---

## Wave 0 — Truth & scaffolding

- [x] W0.1 Inspect repo + git remote + dual-stack map
- [x] W0.2 Write this backlog + AGENTS.md
- [x] W0.3 Add `pyproject.toml` package layout (`src/parrts`)
- [x] W0.4 Root README honesty section + pointer to docs/

## Wave 1 — Modern core RAG (today's tech)

- [x] W1.1 Inventory model + 7-location seed data (deterministic seed) — expanded catalog ~35×7
- [x] W1.2 Embeddings: HashingEmbedder default (offline); optional ST/OpenAI via `PARRTS_EMBEDDER`
- [x] W1.3 FAISS if available else numpy cosine; persist `.parrts/index/`
- [x] W1.4 Hybrid retrieval: dense + BM25/TF + RRF k=60
- [x] W1.5 Optional cross-encoder rerank when available (engine flag)
- [x] W1.6 Traffic-light policy green/yellow/red + confidence + actions
- [x] W1.7 Optional LLM synthesis; graceful offline
- [x] W1.8 Unit tests — offline suite green

## Wave 2 — Backend boot & honesty

- [x] W2.1 `pydantic-settings` BaseSettings
- [x] W2.2 `main.py` lifespan + honest health + soft API router
- [x] W2.3 Async Anthropic/OpenAI; env model IDs (Sonnet 4 / GPT-4.1-mini family)
- [x] W2.4 Modernized `backend/requirements.txt`
- [x] W2.5 `parts_lookup` uses `parrts` when importable
- [x] W2.6 Vector service whitelist + named binds; HNSW note in init.sql
- [x] Model import fixes: Email.Numeric, Shipment.JSON, Supplier.ForeignKey, User.Base, order_item re-export, soft reportlab/MFA deps
- [x] Backend mounts `/query` via parrts core without Postgres

## Wave 3 — Unified surfaces

- [x] W3.1 CLI: `python -m parrts query "…"`
- [x] W3.2 FastAPI thin app `src/parrts/api.py`
- [x] W3.3 Wire root `start_demo.sh` to parrts core (`api|ui|both|backend` modes)
- [x] W3.4 Streamlit dashboard thin client — `src/parrts/ui_streamlit.py`

## Wave 4 — Frontend & DX

- [x] W4.1 Invalid radix packages removed; Next 15.1 / React 18.3
- [x] W4.2 `frontend/lib/api.ts` typed client
- [x] W4.3 Parts page live query + mock fallback + traffic-light badge
- [x] W4.4 `npm install` + `tsc --noEmit` green; CI type-check + build job

## Wave 5 — Agents, eval, ops

- [x] W5.1 LangGraph expanded: parts_lookup node + real edges + parrts fallback
- [x] W5.2 Structured `AgentResult.to_public_dict()` (+ traffic_light / requires_human / correlation_id)
- [x] W5.3 Eval script — hit@k + MRR + recall + latency; default 12/12; extended dataset
- [x] W5.4 docker-compose healthcheck + env_file + profiles (core/api/full/pgvector/obs)
- [x] W5.5 GitHub Actions CI matrix (py 3.11/3.12) + frontend job + compose config
- [x] W5.6 Structured JSON logging (`parrts.logging_utils`) + query span + X-Request-ID middleware

## Wave 6 — Hardening

- [x] W6.1 Auth mode explicit: `AUTH_MODE=demo|production` on settings + root payload
- [x] W6.2 Rate limiting middleware wired (`RATE_LIMIT_ENABLED`, configure from settings)
- [x] W6.3 pgvector production path: `PGVECTOR_ENABLED`, `VECTOR_BACKEND`, backend_status + health/metrics; opt-in SQL path; offline tests
- [x] W6.4 Payment/shipping remain mock unless keys present (pinned non-goal without keys)

## Wave 7 — Max-opt retrieval & ops

- [x] W7.1 Parent-document / multi-location SKU expansion (`parent_expand.py`, CLI `--expand-parent`)
- [x] W7.2 Lazy cross-encoder rerank (no download on import)
- [x] W7.3 BGE/st embedder CLI aliases + status features map
- [x] W7.4 Eval harness metrics: hit@k, MRR, recall@k, latency p50/p95; `--dataset` `--k`
- [x] W7.5 `/metrics` Prometheus stub; health reports vector backend
- [x] W7.6 parrts **v0.4.0**

## Wave 8 — Full `/api/v1` boot chain (2026-07-31 cont)

- [x] W8.1 Fix `auth_service.get_db` NameError
- [x] W8.2 Soft-load each v1 endpoint module (one failure ≠ total blackout)
- [x] W8.3 Rename SQLAlchemy-reserved `metadata` → `extra_data` (barcode + serialized models)
- [x] W8.4 **15/15** v1 routers load; main mounts `/api/v1`
- [x] W8.5 `scripts/verify_boot.py` + `tests/test_backend_boot.py`
- [x] W8.6 CI `backend-smoke` job (`pip install -r backend/requirements.txt`)
- [x] W8.7 parrts **v0.4.1** / API surface 1.3.0

---

## Verify commands

```bash
cd /Users/nexteleven/Desktop/Parrts-Dist-RAG
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api]"
pip install -r backend/requirements.txt   # for full /api/v1
pytest -q
PYTHONPATH=backend:src python scripts/verify_boot.py
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm --expand-parent
python scripts/eval_retrieval.py --dataset default -k 5
```

## Explicit non-goals this loop

- Live Stripe/EasyPost without keys  
- Scraping production supplier sites  
- Full 13-agent production SLA  
- Live BGE model download in CI (optional local extra)  
