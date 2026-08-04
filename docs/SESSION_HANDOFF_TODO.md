# Parts — Session Handoff + Full TODO

**Updated:** 2026-08-04  
**Package:** `parrts` **v0.14.2**  
**SoT:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Ship:** https://github.com/seanebones-lang/parts  

```bash
cd ~/Desktop/Parrts-Dist-RAG && git fetch origin && git log --oneline -5
```

## Where we are

| Layer | Status |
|-------|--------|
| Email desk | Done |
| JWT mint + org FE + OEM beat | Done |
| **Staging commerce smoke (fail closed)** | **Done v0.14.2** |
| Live Stripe/EasyPost/SMTP | Only with real test keys |
| Wave 26 transfers/approvals | Open |

**Tip:** (after push)

## TODO

### Wave 25 — Staging commerce
- [x] Stripe order → PaymentIntent path (`/payments` + order-intent) fail-closed + smoke
- [x] EasyPost rates + label path fail-closed + smoke  
- [x] Email dry-run always; real send only `STAGING_LIVE_EMAIL=1`
- [x] INSTALL §6 staging runbook · `./scripts/staging_commerce_smoke.sh`

### Wave 26 — M2 product depth
- [ ] Inter-store transfer + stock conservation
- [ ] Manager approval threshold (RBAC)
- [ ] Observability baseline docs

### Wave 27–28
Partner OEM / full commerce

## Cont
> Wave 26 transfers/approvals — eng-owned, no billing keys required.

*NextEleven LLC*
