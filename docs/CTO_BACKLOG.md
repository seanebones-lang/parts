# Parts (parrts) — CTO Backlog

**Root:** monorepo (local clone of `seanebones-lang/parts`)  
**Ship:** `https://github.com/seanebones-lang/parts` (`origin` / `main`)  
**Package:** `parrts` **v0.5.0**  
**SoT:** this file. Mark `[x]` only after real execution + verification.

Waves 0–10: complete (see git history). Honesty README landed 2026-07-31.

---

## Wave 11 — Production hardening (senior review 2026-07-31)

### CI / quality gates

- [x] W11.1 Core CI job installs `.[dev,api]` + `PYTHONPATH=backend:src`
- [x] W11.2 Ruff hard-fail (no continue-on-error); import fixes applied
- [x] W11.3 Frontend `npm run build` required
- [x] W11.4 Eval smoke hard-fail on default dataset
- [x] W11.5 Compose config validate hard-fail (dev + prod)

### Frontend ship

- [x] W11.6 Fix `/analytics` `next build` (client shell + dynamic Recharts ssr:false)
- [x] W11.7 Full static generation 15/15 pages
- [x] W11.8 Frontend Dockerfile multi-stage Node 20
- [x] W11.9 Removed invalid `experimental.appDir`

### Security / auth

- [x] W11.10 Production secret guard (`SECRET_KEY` + `DEBUG`)
- [x] W11.11 `.env.example` SECRET_KEY / ENVIRONMENT docs
- [x] W11.12 `require_user_if_production` on mutating inventory/payments/customers/locations/emails/orders/ai_agents/deployment/rollout/parts
- [x] W11.13 Tests extended (auth pattern + boot guard) — **67 passed, 2 skipped**

### Ops

- [x] W11.14 `docker-compose.prod.yml`
- [x] W11.15 Backend Dockerfile monorepo context (`PYTHONPATH=/app:/src`)
- [x] W11.16 Version alignment `parrts` 0.5.0 + README

### Legal / repo hygiene

- [x] W11.17 `pyproject.toml` Proprietary - NextEleven LLC
- [x] W11.18 Legacy root pitch → `archive/legacy-pitch/`
- [x] W11.19 Archive README pointer
- [x] W11.20 Root README honesty + Wave 11 status

### Verify (measured)

```
pytest -q                     → 67 passed, 2 skipped
ruff check src tests          → All checks passed
verify_boot.py                → api_v1 loaded_count=15, parrts green
eval_retrieval default -k 5   → 12/12 hit@5 mrr=1.000 mode=parrts
frontend tsc + build          → exit 0
compose dev + prod config -q  → OK
prod guard insecure SECRET    → RuntimeError (exit 1)
```

## Explicit non-goals Wave 11

- Live Stripe/EasyPost without keys  
- Full multi-tenant RBAC  
- Live pgvector Docker in CI  
- Full 13-agent production SLA  

## Agents

See `docs/AGENTS.md`. Wave 11: CI-OPS ∥ FE-SHIP ∥ BE-SEC + ORCH hygiene/integrate.
