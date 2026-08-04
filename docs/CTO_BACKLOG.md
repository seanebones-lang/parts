# Parts — CTO Backlog

**Ship:** https://github.com/seanebones-lang/parts · **v0.14.2**  
**Handoff:** [`SESSION_HANDOFF_TODO.md`](SESSION_HANDOFF_TODO.md)

| Layer | Status |
|-------|--------|
| Email desk | Production-ready |
| DMS + commerce modules | In system (key-gated) |
| JWT / org FE / OEM beat | In system |
| Staging commerce smoke | **In system** v0.14.2 fail-closed |
| Live pay/ship/email | Requires real test keys |
| Transfers / approvals | Next (Wave 26) |

## Next
1. Wave 26 — inter-store transfer + manager approval  
2. Wave 27+ partner OEM only with contract  

## Never
Fake Stripe/EasyPost/IMAP · OEM scraping · CDK parity

**Staging:** `./scripts/staging_commerce_smoke.sh` · INSTALL §6
