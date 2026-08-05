# Demo / system bring-up

**Package:** v0.20.0 · Prefer `demo_up` / `system_up` from repo root.

```bash
./scripts/system_up.sh    # preferred alias when present
# or
./scripts/demo_up.sh      # ingest + DMS seed/reindex + email seed + API :8000 + UI :3000

# Surfaces
open http://127.0.0.1:3000/emails
open http://127.0.0.1:3000/parts
open http://127.0.0.1:3000/inventory
open http://127.0.0.1:3000/orders
open http://127.0.0.1:3000/analytics
open http://127.0.0.1:3000/supersessions

./scripts/system_smoke.sh   # or ./scripts/demo_smoke.sh
./scripts/system_down.sh    # or ./scripts/demo_down.sh
```

Load catalog:

```bash
parrts dms sync-oem --source file --path ./data/oem/sample_oem_catalog.json --reindex
# live:
# OEM_FEED_URL=... OEM_FEED_TOKEN=... parrts dms sync-oem --source http --reindex
```

Offline note: if API drops mid-demo, create order/customer queues in the browser (banner → Retry when online). SW caches shell only — not DMS JSON.

Product definition: [`SYSTEM.md`](SYSTEM.md) · DMS: [`DMS_OEM.md`](DMS_OEM.md) · Email: [`EMAIL_DESK.md`](EMAIL_DESK.md)
