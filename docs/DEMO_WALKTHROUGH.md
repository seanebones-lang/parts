# Demo / system bring-up

```bash
./scripts/system_up.sh    # preferred alias
# or
./scripts/demo_up.sh

# Counter + DMS UI
open http://127.0.0.1:3000/parts
open http://127.0.0.1:3000/inventory

./scripts/system_smoke.sh
./scripts/system_down.sh
```

Load production catalog:

```bash
parrts dms sync-oem --source file --path ./data/oem/sample_oem_catalog.json --reindex
# live:
# OEM_FEED_URL=... OEM_FEED_TOKEN=... parrts dms sync-oem --source http --reindex
```

Product definition: [`SYSTEM.md`](SYSTEM.md)
