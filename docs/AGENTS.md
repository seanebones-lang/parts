# Specialized Agents — Parrts-Dist-RAG

| Agent ID | Role | Owns (only) | Forbidden |
|----------|------|-------------|-----------|
| **CORE** | Modern hybrid RAG package | `src/parrts/**`, `tests/test_*.py`, `pyproject.toml` | `backend/app/**` except import adapters, `frontend/**` |
| **BE** | Backend boot + honesty | `backend/app/core/**`, `backend/main.py`, `backend/requirements.txt`, `backend/app/services/llm_service.py`, `backend/app/services/vector_service.py`, `backend/app/services/health_service.py`, `backend/app/agents/parts_lookup.py`, `backend/init.sql` | `src/parrts/**`, `frontend/**` |
| **DEMO** | CLI/API surfaces + scripts | `src/parrts/cli.py`, `src/parrts/api.py`, `scripts/**`, `start_demo.sh` (thin), root thin wrappers | Deep agent rewrites |
| **FE** | Frontend deps + API client | `frontend/package.json`, `frontend/lib/**`, `frontend/app/parts/**`, `frontend/app/page.tsx` | `backend/**`, `src/**` |
| **OPS** | Compose, CI, eval | `docker-compose.yml`, `.github/**`, `scripts/eval_retrieval.py`, `tests/eval/**` | Feature logic |
| **AGENTS** | LangGraph wiring | `backend/app/agents/**` | `src/parrts/**` core math |

## Concurrency

Max 3 parallel leaves. Non-overlapping paths only. Children **do not commit**. Orchestrator integrates, tests, commits, pushes.

## Child entry ritual

```bash
cd /Users/nexteleven/Desktop/Parrts-Dist-RAG
pwd && ls -la && git status
```

## Acceptance

- Real pytest green for core  
- `python -m parrts query "…"` returns traffic-light JSON without API keys  
- Backend config imports without error  
- No fake health "connected" without probe  

## Swarm IDs (Wave 0 register)

- swa9790553 architecture truth  
- sw23ea1d5f RAG modernization  
- swd61bc3a7 backend quality  
- sw047650bc frontend/DX  
