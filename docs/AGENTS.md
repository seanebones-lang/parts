# Agent ownership — Parts / Parrts-Dist-RAG

**Root:** monorepo clone of `seanebones-lang/parts`  
**Ship remote:** `origin` → `https://github.com/seanebones-lang/parts`  
**Rule:** children **do not commit**. Orchestrator integrates, verifies, commits, pushes.

| Agent | Owns | Forbidden |
|-------|------|-----------|
| **CI-OPS** | `.github/workflows/ci.yml`, `docker-compose.prod.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `pyproject.toml` (license/version only), `.env.example` | Deep FE page logic, endpoint business logic |
| **FE-SHIP** | `frontend/**` (pages, next.config, package.json if needed) | `backend/**`, `src/**` |
| **BE-SEC** | `backend/main.py` (prod secret guard), `backend/app/core/config.py`, `backend/app/api/deps.py`, `backend/app/api/v1/endpoints/**`, `tests/test_auth_demo_mode.py` | `frontend/**` |
| **HYGIENE** | `archive/legacy-pitch/**`, root markdown moves, `README.md` honesty section, `docs/CTO_BACKLOG.md` checkboxes (orchestrator) | Breaking modern `src/parrts` APIs |
| **ORCH** | Integrate, pytest, verify_boot, eval, next build, commit, push `parts` | — |

## Wave 11 non-overlap

- CI-OPS ∥ FE-SHIP ∥ BE-SEC in parallel  
- HYGIENE after FE/BE (path moves) or sequential by ORCH  
