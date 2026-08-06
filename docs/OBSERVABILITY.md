# Observability baseline (Parts)

**Package:** `parrts` **v0.22.0** · updated through Wave 33  
**Contact:** hello@mothership-ai.com

## What exists today

| Signal | Where | Notes |
|--------|--------|--------|
| HTTP access | uvicorn / reverse proxy | Standard access logs |
| App log level | `LOG_LEVEL` env | backend `settings` |
| Correlation | `parrts.logging_utils` | query spans |
| Health | `GET /health` | Honest degraded when DB down |
| Metrics | `GET /metrics` | Present when boot path loads |
| DMS status | `GET /api/v1/dms/status` | counts + `oem_sync_runs` |
| DMS analytics | `GET /api/v1/dms/analytics` | real tables: orders $, dead stock, fill-rate, pay/ship event counts |
| OEM runs | `parrts dms oem-runs` · `GET /dms/oem/runs` | sync history |
| Transfers | `GET /api/v1/dms/transfers` | status trail |
| Stock adjustments | `GET …/inventory/adjustments` | immutable audit |
| Supersessions | `GET /dms/supersessions` | mapping list |
| Payment ledger | `GET /dms/payments/events` | intents/events — not bank settlement |
| Shipment ledger | `GET /dms/shipments/events` | rates/labels — not carrier SLA |
| Notification ledger | `GET /dms/notifications` · `parrts dms notifications` | drafts/sends — not delivery guarantee without SMTP |
| Compliance export | `GET /dms/compliance/export` · `parrts dms export-audit` | manager+ |
| Email desk | `GET /api/v1/emails/status` | G/Y/R counts |
| Automation | `GET /api/v1/automation/status\|results` · `parrts automation *` | runs + HIL alerts |
| Integrations | system integrations endpoint when mounted | key presence, no secrets |
| CI | GitHub Actions `CI` | core + backend-smoke + FE build |
| FE offline queue | browser localStorage | order/customer mutations only |
| Load baseline | `docs/LOAD_BASELINE.md` · `scripts/load_baseline.py` | offline laptop timings — **not** prod multi-user SLA |

## Structured request logging (baseline)

Module loggers (`logging.getLogger(__name__)`). Recommended on mutating DMS/commerce handlers:

- `request_id` (middleware UUID)
- `path`, `method`, `status`
- `parts_role` (JWT / X-Parts-Role)
- `duration_ms`

Not a full OpenTelemetry/APM stack — do not claim APM.

## p95 / load

Offline baseline checked in (`docs/LOAD_BASELINE.md`).  
Optional k6/vegeta against `/query` and `/api/v1/dms/inventory` in staging.  
Draft target (not enforced): p95 `/query` no-LLM &lt; 300ms with hash embedder.

## Ops checks

```bash
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/api/v1/dms/status | jq '{catalog_parts, backend}'
curl -s http://127.0.0.1:8000/api/v1/dms/analytics | jq '{counts, revenue}'
curl -s http://127.0.0.1:8000/api/v1/automation/results | jq .
curl -s http://127.0.0.1:8000/api/v1/dms/notifications | jq .
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/load_baseline.py
gh run list -R seanebones-lang/parts -L 1
```
