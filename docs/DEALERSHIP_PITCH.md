# Parts — operator brief (dealership)

**Product:** Parts by NextEleven LLC — dealership parts system  
**Repo:** https://github.com/seanebones-lang/parts

---

## One sentence

Counter staff type what the customer says; Parts returns ranked parts across locations with confidence lights, backed by your DMS catalog and OEM/distributor feeds.

---

## Bring the system up

```bash
./scripts/demo_up.sh
# Counter:    http://127.0.0.1:3000/parts
# Inventory:  http://127.0.0.1:3000/inventory
# Orders:     http://127.0.0.1:3000/orders
# Customers:  http://127.0.0.1:3000/customers
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

## Production posture

| Setting | Value |
|---------|--------|
| `ENVIRONMENT` | `production` |
| `AUTH_MODE` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | long random |
| Compose | `docker-compose.prod.yml` |

---

## Objections

| Question | Answer |
|----------|--------|
| Is this the real system? | Yes — Parts is the product: search + DMS + feeds + API + UI. |
| Where does catalog come from? | Your DMS export or live OEM/distributor HTTP feed. |
| Hallucinations? | Traffic-light ranking; human confirms. LLM synthesis optional/off by default. |
| Payments/shipping? | Integrated modules; go live when Stripe/EasyPost keys are configured. |

See `docs/SYSTEM.md` and `docs/DMS_OEM.md`.
