# Observability baseline (Parts)

**Package:** parrts · updated Wave 26

## What exists today

| Signal | Where | Notes |
|--------|--------|--------|
| HTTP access | uvicorn / reverse proxy | Standard access logs |
| App log level | `LOG_LEVEL` env | backend `settings` |
| Health | `GET /health` | Honest degraded when DB down |
| Metrics stub | `GET /metrics` | Present when boot path loads |
| DMS status | `GET /api/v1/dms/status` | counts + `oem_sync_runs` |
| OEM runs | `parrts dms oem-runs` | sync history |
| Transfers | `GET /api/v1/dms/transfers` | status trail on rows |
| Stock adjustments | `GET /api/v1/dms/inventory/adjustments` · `POST …/inventory/adjust` | immutable audit |
| Email desk | `GET /api/v1/emails/status` | G/Y/R counts |
| Integrations | `GET /api/v1/system/integrations` (if mounted) | key presence, no secrets |
| CI | GitHub Actions `CI` | core + backend-smoke + FE build |

## Structured request logging (baseline)

Backend should continue using module loggers (`logging.getLogger(__name__)`).  
Recommended fields on mutating DMS/commerce handlers (when adding more):

- `request_id` (middleware UUID)
- `path`, `method`, `status`
- `parts_role` (from JWT / X-Parts-Role)
- `duration_ms`

Not yet a full OpenTelemetry stack — document only; do not claim APM.

## p95 / load (later)

Optional: k6 or vegeta against `/query` and `/api/v1/dms/inventory` in staging.  
Target draft (not enforced): p95 `/query` no-LLM &lt; 300ms offline hash embedder.

## Ops checks

```bash
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/api/v1/dms/status | jq '{catalog_parts,oem_sync_runs:(.oem_sync_runs|length)}'
PYTHONPATH=backend:src python scripts/verify_boot.py
```
