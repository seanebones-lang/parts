# Parrts-Dist-RAG Roadmap

Last updated: 2026-07-31 (Wave 8)

## Ship target

**GitHub:** https://github.com/seanebones-lang/parts (`origin` / `main`)  
Local: `~/Desktop/Parrts-Dist-RAG`

## Shipped (max-opt loop)

1. `parrts` core hybrid retrieval + traffic-light + offline tests (**v0.4.1**)  
2. Backend boots Pydantic v2 / async LLM / honest health  
3. **Full `/api/v1`**: 15/15 routers soft-loaded (auth get_db + metadata rename)  
4. Frontend typed client + traffic-light badge + type-check CI  
5. CI matrix + backend-smoke + compose profiles + `/metrics`  
6. Parent SKU expansion, lazy rerank, eval MRR/recall/latency  
7. Opt-in pgvector path (`PGVECTOR_ENABLED`)

## Next

- Optional ST/BGE smoke when embeddings extra installed (local download)  
- Seeded pgvector e2e under compose `--profile api` when Docker DB up  
- Wire remaining LangGraph specialists beyond parts_lookup  
- Demo mode JWT-optional hardening pass on mutating routes  

## Later

- Live Stripe / EasyPost when keys present  
- Supplier scraping only behind explicit feature flags  
- Multi-tenant auth hardening  

See `docs/CTO_BACKLOG.md` for checkbox SoT.
