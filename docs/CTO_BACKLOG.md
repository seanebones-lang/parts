# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.12.0**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| **Inbound email auto-answer + G/Y/R desk** | **Production-ready** (selling point) |
| IMAP/SMTP mailbox | **In system** (activates with credentials) |
| AI counter search | **In system** |
| DMS inventory/customers/orders | **In system** (SQLite + Postgres dual-mode) |
| Catalog admin + CSV | **In system** (`/catalog` + import-csv) |
| Order lifecycle + invoice PDF | **In system** (open→picking→invoiced→completed) |
| Light RBAC roles | **In system** (`parrts.rbac` + `/dms/rbac`) |
| Install + backup runbooks | **In system** (`docs/INSTALL.md`, backup/restore scripts) |
| OEM file + HTTP feeds | **In system** (live when URL/token set) |
| Payments / shipping | **In system** — live when Stripe/EasyPost keys set |
| Postgres multi-node HA | **Next** |
| Named OEM partner connectors | **Next** (contracts) |
| Full RO/GL + JWT role claim wire | **Next** |

## Wave 19 — M1 residual close (this ship)

- [x] Catalog upsert + CSV import (core/API/CLI/FE `/catalog`)
- [x] Order lifecycle status machine + cancel restores stock
- [x] Invoice PDF (stdlib writer) + download route
- [x] Light RBAC matrix (`counter|manager|admin`)
- [x] `docs/INSTALL.md` + `scripts/backup_dms.sh` + `restore_dms.sh`
- [x] Tests

## Wave 18 — Pay/ship UI bound

- [x] Stripe/EasyPost key-gated commerce + FE

## Wave 17 — Postgres DMS dual-mode + Alembic

- [x] `DMS_BACKEND` + `001_dms_core`

## Wave 15–16 — Email desk

- [x] Production desk selling point

## M1 single-site GA

- [x] Postgres dual-mode + Alembic
- [x] Catalog admin + CSV
- [x] Order lifecycle + invoice PDF
- [x] RBAC (light matrix; JWT claim wire still optional harden)
- [x] Prod install + backup runbooks
- [x] CI green

## Never
Unauthorized OEM scraping · fake mailbox/Stripe/EasyPost without keys

**Install:** [`INSTALL.md`](INSTALL.md) · **Email:** [`EMAIL_DESK.md`](EMAIL_DESK.md) · **DMS:** [`DMS_OEM.md`](DMS_OEM.md)
