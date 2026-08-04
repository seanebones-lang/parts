# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.13.0**  
**Handoff TODO:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md) ← **start here next session**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| Email desk (selling point) | **Production-ready** |
| AI counter + DMS sqlite/postgres | **In system** |
| Catalog / orders / invoice / pay-ship | **In system** |
| JWT → RBAC enforcement | **In system** (`require_permission`, X-Parts-Role) |
| Multi-rooftop org + location ACL | **Foundation in system** |
| OEM scheduled sync task | **In system** (skip without URL) |
| FE org/ACL UI · beat in compose · JWT mint E2E | **Next** (Wave 22–24) |
| Multi-node HA / partner OEM / RO-GL | **Later** |

## Done waves (summary)

- W15–16 Email desk production  
- W17 Postgres DMS + Alembic  
- W18 Pay/ship UI bound  
- W19 M1 residual (catalog, lifecycle, invoice, install/backup)  
- W20 M2 foundation (RBAC wire, org/ACL, OEM schedule helper)

## Next (see full ordered TODO)

1. Wave 21 — CI green + dual-remote push hygiene  
2. Wave 22 — JWT role mint E2E on login  
3. Wave 23 — Org/ACL FE  
4. Wave 24 — Celery beat OEM nightly in compose  
5. Wave 25 — Staging pay→ship→email with real test keys  

## Never
Unauthorized OEM scraping · fake delivery without keys

**Install:** [`INSTALL.md`](INSTALL.md) · **Email:** [`EMAIL_DESK.md`](EMAIL_DESK.md) · **Handoff:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md)
