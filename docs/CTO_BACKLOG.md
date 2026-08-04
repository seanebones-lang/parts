# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.11.0**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| **Inbound email auto-answer + G/Y/R desk** | **Production-ready** (selling point) |
| IMAP/SMTP mailbox | **In system** (activates with credentials) |
| AI counter search | **In system** |
| DMS inventory/customers/orders | **In system** (SQLite default **+ Postgres dual-mode**) |
| OEM file + HTTP feeds | **In system** (live when URL/token set) |
| Operator UI (core modules) | **In system** |
| Payments / shipping | **In system** — UI + API bound; live when Stripe/EasyPost keys set |
| Postgres multi-node HA | **Next** (dual-mode + Alembic landed; HA/replication later) |
| Named OEM partner connectors | **Next** (contracts) |
| Full RO/GL accounting suite | **Next** |

## Wave 18 — Pay/ship UI bound to services (this ship)

- [x] `parrts.commerce` key-gated Stripe + EasyPost helpers (fail closed)
- [x] `GET /api/v1/payments/config` + `POST /order-intent` (no PG invoice required)
- [x] `GET/POST /api/v1/shipping/config|rates|label` soft-loaded router
- [x] FE `/payments` + `/shipping` forms + Orders Pay/Ship deep links
- [x] Tests: unit fail-closed + offline API 503 without keys
- [x] system integrations reports payments/shipping status + dms_mode

## Wave 17 — Postgres DMS dual-mode + Alembic

- [x] `DMS_BACKEND=sqlite|postgres` + Alembic `001_dms_core` + migrate CLI

## Wave 16 — Email desk production

- [x] IMAP/SMTP + human workflow + Celery + FE desk

## Wave 15 — Email desk revival

- [x] Offline core + CLI + API + FE + demo seed + tests

## Wave 14 — Product identity + system hardening

- [x] Kill pilot framing · SYSTEM.md · system_up aliases · product nav
- [x] Postgres dual-mode for DMS (same API) — v0.10.0
- [x] Alembic migrations for server profile — `001_dms_core`
- [x] Payments/shipping UI bound to services when keys present — v0.11.0

## M1 residual (next)

- [ ] Catalog admin + CSV UI
- [ ] Full order lifecycle + invoice PDF
- [ ] RBAC
- [ ] Prod install + backup runbooks

## Never
Unauthorized OEM scraping · fake mailbox delivery without SMTP · fake Stripe charges / EasyPost labels without keys · claiming live IMAP without credentials

**Email desk:** [`EMAIL_DESK.md`](EMAIL_DESK.md) · **Roadmap:** [`ROADMAP_TO_COMPLETION.md`](ROADMAP_TO_COMPLETION.md) · **DMS:** [`DMS_OEM.md`](DMS_OEM.md)
