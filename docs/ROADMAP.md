# Parrts-Dist-RAG Roadmap

Last updated: 2026-07-31 (Wave 11)

## Ship target

**GitHub:** https://github.com/seanebones-lang/parts (`origin` / `main`)  
Local: `~/Desktop/Parrts-Dist-RAG`  
Package: **parrts v0.5.0**

## Shipped

### Waves 0–10
Hybrid RAG core, backend 15/15 boot, FE typed client, LangGraph specialists, pgvector seed, AUTH_MODE demo/prod deps, eval harness.

### Wave 11 — production hardening
- Hard-fail CI (ruff, eval, FE build, compose)
- Next.js production build fixed (analytics/Recharts SSR)
- Production secret guard + write-route JWT wiring
- `docker-compose.prod.yml` + monorepo Dockerfiles
- Proprietary license metadata aligned
- Legacy pitch archived under `archive/legacy-pitch/`

## Optional next

- Live Docker Desktop pgvector seed + e2e in a staging env  
- ST/BGE embedder for real catalog synonymy  
- Live Stripe/EasyPost when keys present  
- Multi-tenant RBAC / org isolation  
- Alembic migrations instead of `create_all`  
- Disable `/docs` behind auth in production  

See `docs/CTO_BACKLOG.md` for checkbox SoT.
