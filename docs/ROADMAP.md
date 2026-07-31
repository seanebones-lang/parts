# Parrts-Dist-RAG Roadmap

Last updated: 2026-07-31 (Wave 10)

## Ship target

**GitHub:** https://github.com/seanebones-lang/parts (`origin` / `main`)  
Local: `~/Desktop/Parrts-Dist-RAG`

## Shipped (max-opt Waves 0–10)

1. `parrts` core hybrid RAG + traffic-light + offline tests (**v0.4.2**)  
2. Backend Pydantic v2 / async LLM / honest health / 15/15 `/api/v1`  
3. Frontend typed client + traffic-light + type-check CI  
4. CI matrix + backend-smoke + compose profiles + `/metrics`  
5. Parent expand, lazy rerank, eval MRR/recall/latency  
6. LangGraph full specialist graph (soft offline)  
7. pgvector seed script + skippable e2e (no Docker required for CI)  
8. AUTH_MODE demo/production JWT deps on mutating routes  
9. Mocked agent unit tests (inventory/payment/shipping)

## Optional next (keys / Docker daemon)

- Start Docker Desktop → `docker compose --profile pgvector up -d` → `PGVECTOR_ENABLED=true python scripts/seed_pgvector.py`  
- Live ST/BGE: `PARRTS_TEST_ST=1 pytest tests/test_optional_st_embedder.py`  
- Live Stripe/EasyPost when keys present  
- Wire remaining write endpoints to `require_user_if_production`  
- Multi-tenant auth hardening  

See `docs/CTO_BACKLOG.md` for checkbox SoT.
