# Parrts-Dist-RAG Roadmap

Last updated: 2026-07-31

## Now (max-opt loop)

1. Ship `parrts` core hybrid retrieval + traffic-light policy + tests  
2. Backend boots on modern Pydantic v2 / async LLM clients / honest health  
3. Frontend deps valid + typed API client  
4. CI + compose healthchecks  

## Next

- Wire full LangGraph specialist graph to core retrieval  
- Retrieval eval harness (precision@k on fixed dealership queries)  
- pgvector path as production profile alongside local FAISS  
- Optional cross-encoder rerank when torch present  

## Later

- Live Stripe / EasyPost when keys present  
- Supplier scraping only behind explicit feature flags  
- Multi-tenant auth hardening  

See `docs/CTO_BACKLOG.md` for checkbox SoT.
