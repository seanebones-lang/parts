# Parts — CTO Backlog

**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.14.1**  
**Handoff:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md)

## Completeness

| Layer | Status |
|-------|--------|
| Email desk | Production-ready |
| DMS + catalog/orders/pay-ship | In system |
| JWT RBAC + role mint | In system |
| Org/ACL FE | In system v0.14.0 |
| OEM Celery beat nightly | **In system** v0.14.1 (skip without URL) |
| Staging real keys path | Next (Wave 25) |
| HA / partner OEM / RO-GL | Later |

## Done recently
W22 JWT mint · W23 `/orgs` · **W24 OEM beat + oem_sync_runs CLI/API**

## Next
1. Wave 25 — staging Stripe/EasyPost/email with real test keys  
2. Wave 26 — transfers / approvals  

## Never
Unauthorized OEM scraping · fake delivery without keys
