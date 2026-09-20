# Parts Platform — Full Bug & Health Check Report

> **Archive snapshot (2026-07-31).** Numbers below are historical.  
> **Current product truth:** `parrts` **v0.22.0** · tip `git log -1` · see root `README.md` + `docs/SYSTEM.md` + `docs/TEAM_UPDATE_DOCS_v0.22.0.md`.  
> Re-run health before sales claims: `pytest`, `verify_boot`, `eval_retrieval`, `npm run build`, `gh run list -R seanebones-lang/parts -L 1`.

**Product:** NextEleven Parts (repo: [seanebones-lang/parts](https://github.com/seanebones-lang/parts))  
**Local path:** `~/Desktop/Parrts-Dist-RAG`  
**Commit checked (this report):** `7cecc99` (main) — **stale vs current tip**  
**Date:** 2026-07-31  
**Checker:** Hermes Agent (automated)  
**Contact:** hello@mothership-ai.com

---

## Executive verdict

| Area | Status | Notes |
|------|--------|--------|
| Core hybrid RAG (`parrts`) | **PASS** | Offline retrieval + traffic-light green |
| Unit / integration tests | **PASS** | 59 passed, 2 skipped (by design) |
| Backend `/api/v1` boot | **PASS** | 15/15 routers loaded |
| Frontend TypeScript | **PASS** | `tsc --noEmit` exit 0 |
| Retrieval quality | **PASS** | hit@5 12/12, MRR 1.0, ~0.7 ms mean |
| Docker / live Postgres | **SKIP / BLOCKED** | Docker daemon not running; seed exits clean skipped |
| Live LLM / Stripe / EasyPost | **N/A** | No keys required for core path; mocks by design |
| Ruff style | **WARN** | 24 style issues (import order etc.); not runtime blockers |

**Overall health: GREEN for demo / offline / CI-core path.**  
**Production full-stack needs Docker + Postgres + optional API keys.**

---

## Measured results

### Pytest
```
59 passed, 2 skipped in ~1.6s
```
Skipped intentionally:
1. Optional sentence-transformers / BGE smoke (`PARRTS_TEST_ST=1`)
2. Live pgvector e2e when database unreachable

### Boot smoke (`scripts/verify_boot.py`)
- config: OK (AUTH_MODE=demo, PGVECTOR_ENABLED=false)
- api_v1: **15 loaded, 0 failed** (auth, health, locations, customers, parts, inventory, orders, payments, analytics, emails, ai_agents, barcode, serialized, deployment, rollout)
- main_app: `/`, `/health`, `/query`, `/metrics` present; api_v1 mounted
- parrts: 3 hits, traffic_light **green**

### Retrieval eval (`scripts/eval_retrieval.py`)
```
mode=parrts
hit_rate@5 = 12/12 = 100%
mrr=1.000  recall@5=1.000
lat_mean≈0.7ms
```

### Sample query
```
query: "brake pads for 2019 Honda Civic" --no-llm
→ traffic_light: green
→ top SKU: BP-HC19-L4 (multi-location catalog)
```

### Frontend
```
npx tsc --noEmit → exit 0
```

### Compose
```
docker compose --profile core|api config → OK (YAML valid)
Live containers: not started (daemon offline)
```

### pgvector seed
```
python scripts/seed_pgvector.py
→ ok=true, skipped=true, reason=db_unreachable
→ exit 0 (correct graceful behavior)
```

---

## Known issues (honest)

### Non-blocking
1. **Ruff:** ~24 lint findings (import placement, style). Does not fail tests or boot.
2. **Editable install drift:** after some sessions `python -m parrts` may need `pip install -e ".[dev]"` again in the venv.
3. **Marketing docs in repo root** still mix aspirational language (13-agent full SLA, live Stripe) with reality — use the new README honesty section + this report for sales technical truth.
4. **Next.js** still on a 15.1.x line; npm audit may report advisories — upgrade path is separate release work.
5. **AUTH_MODE production** JWT wired on sample mutating routes (parts bulk-import, orders create); not every write endpoint yet.

### Environment-blocked (not code bugs)
1. Docker Desktop not running → no live pgvector / full compose stack this run.
2. No OPENAI/ANTHROPIC/STRIPE/EASYPOST keys → LLM synthesis, live pay, live ship stay mock/offline.
3. BGE embedder path untested without `PARRTS_TEST_ST=1` + download.

---

## Risk register (buyer-facing technical)

| Risk | Severity | Mitigation already in product |
|------|----------|-------------------------------|
| Hallucinated stock answers | Med | Traffic-light green/yellow/red + human-in-loop on yellow/red |
| Dependency on cloud LLM | Low for lookup | Offline hash embedder + deterministic answers without keys |
| Postgres outage | Med for enterprise API | Core `/query` works without Postgres via `parrts` |
| Auth misconfiguration | Med | Explicit `AUTH_MODE=demo|production` |
| Over-sold “13 agents production” | High if sold as SLA | Sell hybrid RAG + agent **orchestration** with honest maturity tiers |

---

## Recommended pre-demo checklist

```bash
cd ~/Desktop/Parrts-Dist-RAG
source .venv/bin/activate
pip install -e ".[dev,api]"
pip install -r backend/requirements.txt
pytest -q
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/eval_retrieval.py
# Optional full stack:
# open Docker Desktop, then:
# docker compose --profile api up -d
# PGVECTOR_ENABLED=true python scripts/seed_pgvector.py
```

---

## Sign-off

Health check completed **2026-07-31**. Core product is **demo-ready offline**. Full multi-service production path is **code-ready, environment-gated**.

Prepared for NextEleven LLC sales & engineering handoff.
