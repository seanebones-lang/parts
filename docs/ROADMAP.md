# Parrts-Dist-RAG Roadmap

Last updated: 2026-07-31 (Wave 9)

## Ship target

**GitHub:** https://github.com/seanebones-lang/parts (`origin` / `main`)  
Local: `~/Desktop/Parrts-Dist-RAG`

## Shipped (max-opt loop)

1. `parrts` core hybrid retrieval + traffic-light + offline tests (**v0.4.2**)  
2. Backend boots Pydantic v2 / async LLM / honest health  
3. **Full `/api/v1`**: 15/15 routers soft-loaded  
4. Frontend typed client + traffic-light badge + type-check CI  
5. CI matrix + backend-smoke + compose profiles + `/metrics`  
6. Parent SKU expansion, lazy rerank, eval MRR/recall/latency  
7. Opt-in pgvector path (`PGVECTOR_ENABLED`)  
8. LangGraph full specialist graph (soft offline stubs)  
9. Pydantic v2 schema hygiene (auth/location)

## Next

- Seeded pgvector e2e under compose `--profile api` when Docker DB up  
- Demo mode optional JWT on mutating `/api/v1` routes (production already expects JWT)  
- Live ST/BGE local smoke: `PARRTS_TEST_ST=1 pytest -q tests/test_optional_st_embedder.py`  
- Deeper agent unit tests with mocked InventoryService / Stripe  

## Later

- Live Stripe / EasyPost when keys present  
- Supplier scraping only behind explicit feature flags  
- Multi-tenant auth hardening  

See `docs/CTO_BACKLOG.md` for checkbox SoT.
