# Parrts-Dist-RAG Roadmap

Last updated: 2026-07-31 (Wave 7)

## Shipped (max-opt loop)

1. `parrts` core hybrid retrieval + traffic-light policy + offline tests  
2. Backend boots on modern Pydantic v2 / async LLM clients / honest health  
3. Frontend deps valid + typed API client + traffic-light badge  
4. CI matrix + compose profiles + `/metrics` stub  
5. Parent SKU expansion, lazy rerank, eval MRR/recall/latency  
6. Opt-in pgvector production path (`PGVECTOR_ENABLED`)

## Next

- Live ST/BGE smoke when embeddings extra installed (optional download)  
- Wire remaining LangGraph specialists beyond parts_lookup  
- Full `/api/v1` clean install from backend/requirements in CI  
- End-to-end Docker demo profile with seeded pgvector embeddings  

## Later

- Live Stripe / EasyPost when keys present  
- Supplier scraping only behind explicit feature flags  
- Multi-tenant auth hardening  

See `docs/CTO_BACKLOG.md` for checkbox SoT.
