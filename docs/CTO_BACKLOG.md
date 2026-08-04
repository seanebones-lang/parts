# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.13.1**  
**Handoff TODO:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md) ← **start here next session**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| Email desk (selling point) | **Production-ready** |
| AI counter + DMS sqlite/postgres | **In system** |
| Catalog / orders / invoice / pay-ship | **In system** |
| JWT → RBAC enforcement | **In system** (`require_permission`, X-Parts-Role) |
| JWT role mint on login/refresh | **In system** (`role` + `parts_role` claims) v0.13.1 |
| Multi-rooftop org + location ACL | **Foundation in system** |
| OEM scheduled sync task | **In system** (skip without URL) |
| FE org/ACL UI · beat in compose | **Next** (Wave 23–24) |
| Multi-node HA / partner OEM / RO-GL | **Later** |

## Done waves (summary)

- W15–16 Email desk production  
- W17 Postgres DMS + Alembic  
- W18 Pay/ship UI bound  
- W19 M1 residual (catalog, lifecycle, invoice, install/backup)  
- W20 M2 foundation (RBAC wire, org/ACL, OEM schedule helper)  
- W21 CI green hygiene  
- **W22 JWT role mint E2E** (login/refresh claims + prod counter 403)

## Next (see full ordered TODO)

1. Wave 23 — Org/ACL FE  
2. Wave 24 — Celery beat OEM nightly in compose  
3. Wave 25 — Staging pay→ship→email with real test keys  
4. Wave 26 — M2 product depth (transfers, approvals)

## Never
Unauthorized OEM scraping · fake delivery without keys

**Install:** [`INSTALL.md`](INSTALL.md) · **Email:** [`EMAIL_DESK.md`](EMAIL_DESK.md) · **Handoff:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md)
