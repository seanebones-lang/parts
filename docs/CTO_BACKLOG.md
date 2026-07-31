# Parts — CTO Backlog

**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.6.0**  
**Honesty:** `[x]` only after measured verify. Never invent live OEM credentials.

## Strategic truth

| Goal | Reality after W13 |
|------|-------------------|
| Full DMS *replacement* | Multi-quarter vs CDK/Reynolds. **W13 ships a working offline DMS core.** |
| Live OEM feed | Needs contracts. **W13 ships pluggable adapters; HTTP goes live when URL+token set.** |
| Counter AI search | Done (W12). |

## Wave 13 — complete

- [x] W13.1–5 `src/parrts/dms/` SQLite + services + CLI
- [x] W13.6–9 OEM synthetic/file/http + sample feed + tests
- [x] W13.10–12 `/api/v1/dms/*` soft-load (16 routers)
- [x] W13.13–17 FE inventory/orders/customers Live + nav
- [x] W13.18 `docs/DMS_OEM.md`
- [x] W13.19–20 README + pytest + build

### Measured
- `tests/test_dms_oem.py` + `test_dms_api.py` green
- verify_boot `loaded_count=16` includes `dms`
- `parrts dms seed` → 40 parts / 7 locations
- FE build green (`/inventory` `/orders` `/customers` live)

## Later
W14 Postgres/Alembic · W15 named OEM connectors 📌 · W16 RO/GL · W17 multi-tenant

## Never
Unauthorized OEM scraping · fake Honda live API · claiming full DMS GA parity
