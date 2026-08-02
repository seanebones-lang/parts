# Agent ownership — Email desk + DMS

**Root:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Ship:** `origin` → `https://github.com/seanebones-lang/parts`  
**Children do not commit.**

## Wave 15 — Email desk (selling point)

| Agent | Owns | Forbidden |
|-------|------|-----------|
| **EMAIL-CORE** | `src/parrts/email/**`, CLI `email` subcommands, `tests/test_email_desk.py` | FE deep, Postgres email model thrash |
| **EMAIL-BE** | `backend/app/api/v1/endpoints/emails.py`, ai_agents process-email bridge, `tests/test_email_api.py` | `src/parrts/email` schema thrash |
| **EMAIL-FE** | `frontend/app/emails/**`, `frontend/lib/email-api.ts`, nav/home CTAs | backend models |
| **ORCH** | integrate, docs, verify, commit, push | — |

## Wave 13 — DMS + OEM (stable)

| Agent | Owns | Forbidden |
|-------|------|-----------|
| **DMS-CORE** | `src/parrts/dms/**`, `src/parrts/cli.py` (dms subcommands), `tests/test_dms_*.py`, `data/oem/**` | frontend deep, backend endpoints |
| **DMS-BE** | `backend/app/api/v1/endpoints/dms*.py`, `backend/app/api/v1/api.py` include, `backend/app/services/dms_*.py` if needed | `src/parrts/dms` schema thrash |
| **DMS-FE** | `frontend/app/inventory/**`, `orders/**`, `customers/**`, `navigation.tsx`, `lib/dms-api.ts` | backend models |

Parallel: EMAIL-CORE ∥ EMAIL-BE ∥ EMAIL-FE after CORE lands shapes (FE can mock then swap).
