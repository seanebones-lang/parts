# Agent ownership — Parts monorepo

**Root:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Ship:** `origin` → `https://github.com/seanebones-lang/parts`  
**Legacy mirror:** `legacy` → `https://github.com/seanebones-lang/Parrts-Dist-RAG`  
**Handoff:** `docs/SESSION_HANDOFF_TODO.md` · **CTO SoT:** `docs/CTO_BACKLOG.md`  
**Package:** `parrts` v0.22.0  
**Children do not commit.** Orchestrator integrates, verifies, dual-pushes.

## Stable lanes

| Agent | Owns | Forbidden |
|-------|------|-----------|
| **EMAIL-CORE** | `src/parrts/email/**`, CLI `email.*`, `tests/test_email_desk.py` | FE deep, Postgres email thrash |
| **EMAIL-BE** | `backend/app/api/v1/endpoints/emails.py`, email Celery tasks, `tests/test_email_api.py` | email schema thrash from BE |
| **EMAIL-FE** | `frontend/app/emails/**`, `lib/email-api.ts` | backend models |
| **DMS-CORE** | `src/parrts/dms/**`, CLI `dms.*`, `tests/test_dms_*.py`, `tests/test_shipment_ledger.py`, `tests/test_supersession.py`, `data/oem/**` | FE deep, BE endpoint thrash of schema |
| **DMS-BE** | `backend/app/api/v1/endpoints/dms.py`, shipping/payments bridges to DMS ledger, `tests/test_dms_api.py` | rewrite `src/parrts/dms` tables from BE |
| **DMS-FE** | `frontend/app/{inventory,orders,customers,transfers,analytics,supersessions,catalog,orgs}/**`, `lib/dms-api.ts`, nav | backend models |
| **COMMERCE-FE** | `frontend/app/{payments,shipping}/**`, `lib/commerce-api.ts` | invent charges/labels |
| **PWA-FE** | `frontend/public/{sw.js,manifest.webmanifest,icon-*}`, `components/{offline-queue-banner,pwa-register}.tsx`, `lib/offline-queue.ts` | cache API JSON in SW |
| **AUTO-CORE** | `src/parrts/automation/**`, CLI `automation.*`, `tests/test_automation.py` | FE deep |
| **AUTO-BE** | `backend/app/api/v1/endpoints/automation.py` | rewrite automation schema from BE |
| **AUTO-FE** | `frontend/app/results/**`, `lib/automation-api.ts`, email desk order bridge buttons | backend models |
| **DOCS** | `README.md`, `docs/**` (honesty only after measured ship) | checkbox lies |
| **ORCH** | integrate, pytest/eval/verify_boot, commit, push origin+legacy | — |

## Parallel rules

- Non-overlapping paths only  
- If `delegate_task` multi-agent beta 400 → **parent executes**  
- ASYNC batch complete after integrate → **ack only**  

## Verify (ORCH)

```bash
cd /Users/nexteleven/Desktop/Parrts-Dist-RAG
ruff check src tests
PYTHONPATH=backend:src pytest -q --ignore=tests/test_dms_api.py --ignore=tests/test_email_api.py # + other core ignores per CI
PYTHONPATH=backend:src pytest -q tests/test_dms_api.py tests/test_email_api.py tests/test_backend_boot.py
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/eval_retrieval.py -k 5
cd frontend && npm run type-check && npm run build
git push origin main && git push legacy main
```
