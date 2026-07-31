# Agent ownership — Wave 13 DMS + OEM

**Root:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Ship:** `origin` → `https://github.com/seanebones-lang/parts`  
**Children do not commit.**

| Agent | Owns | Forbidden |
|-------|------|-----------|
| **DMS-CORE** | `src/parrts/dms/**`, `src/parrts/cli.py` (dms subcommands), `tests/test_dms_*.py`, `data/oem/**` | frontend deep, backend endpoints |
| **DMS-BE** | `backend/app/api/v1/endpoints/dms*.py`, `backend/app/api/v1/api.py` include, `backend/app/services/dms_*.py` if needed | `src/parrts/dms` schema thrash |
| **DMS-FE** | `frontend/app/inventory/**`, `orders/**`, `customers/**`, `navigation.tsx`, `lib/dms-api.ts` | backend models |
| **ORCH** | integrate, docs, verify, commit, push | — |

Parallel: CORE ∥ BE ∥ FE after CORE lands store API shapes (FE can mock then swap).
