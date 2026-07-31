# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system** (not a pilot demo shell).  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.7.0**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| AI counter search | **In system** |
| DMS inventory/customers/orders | **In system** (embedded SQLite; server PG path next) |
| OEM file + HTTP feeds | **In system** (live when URL/token set) |
| Operator UI (core modules) | **In system** |
| Payments / shipping | **In system as integrations** (activate with keys) |
| Postgres multi-node HA | **Next** |
| Named OEM partner connectors | **Next** (contracts) |
| Full RO/GL accounting suite | **Next** |

## Wave 14 — Product identity + system hardening (this ship)

- [x] Kill pilot/design-partner framing in README, UI, docs
- [x] `docs/SYSTEM.md` as product definition
- [x] `scripts/system_up|down|smoke` aliases
- [x] Nav/home as production product language
- [ ] Postgres dual-mode for DMS (same API)
- [ ] Payments/shipping UI bound to services when keys present
- [ ] Alembic migrations for server profile

## Never
Unauthorized OEM scraping · calling integrations “fake” when they are key-gated production modules
