# AI Workflow Automation — MIN bar (white-label)

**Product:** Parts by NextEleven LLC  
**Package:** `parrts` · this doc is the eng contract for the workflow MIN surface  
**No dealer co-branding** in product UI/docs — generic white-label only.

## What MIN means

A dealer can run **AI agent workflow automation** for parts ops:

| Capability | Done means |
|------------|------------|
| Email intake → classify → specialist → G/Y/R | Live (`/emails`) |
| Human-in-the-loop (HIL) | Override grade, approve/send, confirm order |
| Missing-field / error alerts | Structured alerts when SKU/sender/etc. missing or pipeline errors |
| Automation run recording | Every email process writes a run to `.parrts/automation.db` |
| Results page (daily/always) | `/results` + `GET /api/v1/automation/results` + `parrts automation results` |
| Email → DMS draft order | Preview by default; `--confirm` / Confirm button reserves stock |
| Rulesets | `.parrts/rulesets.json` — operator-tunable HIL / required fields |
| Backend middleware | FastAPI soft-loaded `/api/v1/automation/*` |
| DMS connectivity | Always (local SQLite / Postgres dual-mode) |
| CRM / accounting | **Fail closed** until dealer credentials — flags in rulesets only |

## Explicit non-goals

- Dealer-specific branding in the product  
- Invented CRM/ERP/accounting API calls without credentials  
- Silent auto-order without HIL when `require_human_confirm=true`  
- CDK/Reynolds parity claims  

## Surfaces

| Layer | Path |
|-------|------|
| Core | `src/parrts/automation/**` |
| Email hook | `EmailPipeline.process_id` → `record_email_processed` |
| API | `backend/app/api/v1/endpoints/automation.py` → `/api/v1/automation` |
| FE | `/results`, Email Desk draft/confirm order |
| CLI | `parrts automation status\|results\|runs\|alerts\|resolve\|rulesets\|email-to-order` |
| Tests | `tests/test_automation.py` |

## Verify

```bash
cd ~/Desktop/Parrts-Dist-RAG
PYTHONPATH=src pytest -q tests/test_automation.py
PYTHONPATH=src python -m parrts email seed --clear
PYTHONPATH=src python -m parrts automation results
PYTHONPATH=backend:src python scripts/verify_boot.py   # automation in loaded
```
