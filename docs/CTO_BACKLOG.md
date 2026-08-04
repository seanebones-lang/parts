# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.13.0**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| Email desk (selling point) | **Production-ready** |
| AI counter + DMS sqlite/postgres | **In system** |
| Catalog / orders / invoice / pay-ship | **In system** |
| JWT → RBAC enforcement | **In system** (`require_permission`, X-Parts-Role) |
| Multi-rooftop org + location ACL | **Foundation in system** |
| OEM scheduled sync task | **In system** (Celery `oem.scheduled_sync`, skip without URL) |
| Multi-node HA / partner OEM connectors | **Next** |
| Full RO/GL | **Next** |

## Wave 20 — M2 foundation (this ship)

- [x] `require_permission(perm)` FastAPI dep (demo header + prod JWT role)
- [x] Role aliases (user→counter, superuser→admin) + JWT claim `role`/`parts_role`
- [x] Wire DMS seed/oem/catalog/import/reindex/invoice + cancel permission
- [x] Orgs + location.org_id + user_location_acl filter on inventory
- [x] API `/dms/orgs` `/locations` `/acl/{user}` 
- [x] Celery OEM schedule helper fail-closed without `OEM_FEED_URL`
- [x] Tests

## Waves 15–19

- [x] Email desk · Postgres DMS · commerce · M1 residual

## Next

- JWT role claim on token mint path end-to-end with real login
- Org UI + location picker in FE
- Beat schedule entry for OEM nightly in compose
- Staging pay→ship→email with test keys

## Never
Unauthorized OEM scraping · fake delivery without keys

**Install:** [`INSTALL.md`](INSTALL.md) · **Email:** [`EMAIL_DESK.md`](EMAIL_DESK.md)
