# Parts — operator brief (dealership)

**Product:** Parts by NextEleven LLC — dealership parts system  
**Package:** `parrts` **v0.22.0**  
**Repo:** https://github.com/seanebones-lang/parts  
**Brand:** NextEleven Parts white-label only  
**Contact:** hello@mothership-ai.com · mothership-ai.com

---

## One sentence

Counter staff type what the customer says; Parts returns ranked parts across locations with confidence lights, backed by your DMS catalog, email desk, automation results, and OEM/distributor feeds when configured.

---

## Bring the system up

```bash
./scripts/demo_up.sh
# Email desk: http://127.0.0.1:3000/emails   ← selling point
# Counter:    http://127.0.0.1:3000/parts
# Inventory:  http://127.0.0.1:3000/inventory
# Orders:     http://127.0.0.1:3000/orders    (+ Notify dry-run)
# Results:    http://127.0.0.1:3000/results   (automation HIL)
# Analytics:  http://127.0.0.1:3000/analytics
# Supersessions: http://127.0.0.1:3000/supersessions
# API docs:   http://127.0.0.1:8000/docs
```

Load **your** catalog:

```bash
parrts dms sync-oem --source file --path /path/to/export.json --reindex
# or live:
export OEM_FEED_URL=... OEM_FEED_TOKEN=...
parrts dms sync-oem --source http --reindex
```

---

## What you can show today (honest)

| Live | Needs keys / contract |
|------|------------------------|
| Email desk G/Y/R + search + human approve | Live IMAP/SMTP |
| Multi-location search + traffic light | — |
| DMS inventory / orders / customers / transfers / adjust | — |
| Analytics from real DMS events | — |
| Supersession maps | — |
| Automation runs + HIL + email→order (`/results`) | — |
| Customer notify dry-run ledger (Orders **Notify**) | Live SMTP for real send |
| Offline queue for order/customer creates | — |
| Light installable PWA shell | — |
| Offline load baseline numbers | — (laptop timings only) |
| Stripe pay / EasyPost ship | Live keys (else fail closed) |
| Live OEM feed | Feed URL/token or partner contract |

**Do not claim:** full CDK/Reynolds replacement, live OEM without credentials, fake payment/shipping success, silent email delivery without SMTP, dealer co-brand.

---

## Production posture

| Setting | Value |
|---------|--------|
| `ENVIRONMENT` | `production` |
| `AUTH_MODE` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | long random |
| Compose | `docker-compose.prod.yml` |

See `docs/SYSTEM.md`, `docs/DMS_OEM.md`, `docs/AUTOMATION.md`.
