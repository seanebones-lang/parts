# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system**.  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.14.0**  
**Handoff TODO:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md) ← **start here next session**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| Email desk (selling point) | **Production-ready** |
| AI counter + DMS sqlite/postgres | **In system** |
| Catalog / orders / invoice / pay-ship | **In system** |
| JWT → RBAC + role mint | **In system** v0.13.1 |
| Multi-rooftop org + location ACL | **In system** (API + **FE `/orgs`**) v0.14.0 |
| OEM scheduled sync task | **In system** (skip without URL) |
| Celery beat OEM nightly in compose | **Next** (Wave 24) |
| Multi-node HA / partner OEM / RO-GL | **Later** |

## Done waves (summary)

- W15–16 Email desk production  
- W17–19 M1 DMS/commerce residual  
- W20–22 M2 RBAC + JWT mint  
- **W23 Org/ACL operator UI** (`/orgs`, inventory user_key filter)

## Next

1. Wave 24 — Celery beat OEM nightly in compose  
2. Wave 25 — Staging pay→ship→email with real test keys  
3. Wave 26 — M2 depth (transfers, approvals)

## Never
Unauthorized OEM scraping · fake delivery without keys

**Install:** [`INSTALL.md`](INSTALL.md) · **Handoff:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md)
