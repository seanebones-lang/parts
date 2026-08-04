# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.10.0**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| **Inbound email auto-answer + G/Y/R desk** | **Production-ready** (selling point) |
| IMAP/SMTP mailbox | **In system** (activates with credentials) |
| AI counter search | **In system** |
| DMS inventory/customers/orders | **In system** (SQLite default **+ Postgres dual-mode**) |
| OEM file + HTTP feeds | **In system** (live when URL/token set) |
| Operator UI (core modules) | **In system** |
| Payments / shipping | **In system as integrations** (activate with keys) |
| Postgres multi-node HA | **Next** (dual-mode + Alembic landed; HA/replication later) |
| Named OEM partner connectors | **Next** (contracts) |
| Full RO/GL accounting suite | **Next** |

## Wave 17 — Postgres DMS dual-mode + Alembic (this ship)

- [x] `DMS_BACKEND=sqlite|postgres` + `DMS_DATABASE_URL` / `POSTGRES_*`
- [x] `PostgresDmsStore` same SQL surface as SQLite (`?` → `%s`)
- [x] Alembic `001_dms_core` + `parrts dms migrate`
- [x] CLI `--backend` / `--database-url`
- [x] Unit tests + skip-friendly live Postgres tests
- [x] Docs + `.env.example`

## Wave 16 — Email desk production

- [x] IMAP fetch + SMTP send (stdlib, credential-gated, fail closed)
- [x] `EMAIL_AUTO_SEND` for green-only auto SMTP
- [x] Human override grade + approve/send dry-run + draft patch + polish hook
- [x] Celery tasks wired to `parrts.email.EmailService`
- [x] CLI mailbox/fetch-imap/send/override
- [x] API + FE desk actions + mailbox status
- [x] demo_smoke email path
- [x] Tests for override/send/red-block/mailbox
- [x] Docs + `.env.example`

## Wave 15 — Email desk revival

- [x] Offline core + CLI + API + FE + demo seed + tests

## Wave 14 — Product identity + system hardening

- [x] Kill pilot framing · SYSTEM.md · system_up aliases · product nav
- [x] Postgres dual-mode for DMS (same API) — v0.10.0
- [x] Alembic migrations for server profile — `001_dms_core`
- [ ] Payments/shipping UI bound to services when keys present

## Never
Unauthorized OEM scraping · fake mailbox delivery without SMTP · claiming live IMAP without credentials

**Email desk:** [`EMAIL_DESK.md`](EMAIL_DESK.md) · **Roadmap:** [`ROADMAP_TO_COMPLETION.md`](ROADMAP_TO_COMPLETION.md) · **DMS:** [`DMS_OEM.md`](DMS_OEM.md)
