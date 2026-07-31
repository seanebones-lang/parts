# DMS Core + OEM Feed

## What this is

**Parts DMS Core** is an offline-capable dealership operations layer:

- Local SQLite DB at `.parrts/dms.db` (no Postgres required for pilot)
- Catalog, multi-location inventory, customers, orders
- Pluggable **OEM feed adapters** to load manufacturer/distributor catalogs
- Bridge into AI search (`parrts` hybrid RAG) after sync

This is **not** CDK/Reynolds feature parity. It is a real, runnable core a design partner can operate while feeds and accounting integrations are added.

## OEM feed adapters

| Adapter | When |
|---------|------|
| `synthetic` | Demo / CI — deterministic catalog |
| `file` | Dealer CSV/JSON export dropped on disk |
| `http` | Live feed when `OEM_FEED_URL` (+ optional `OEM_FEED_TOKEN`) is set |

### File format (JSON)

```json
[
  {
    "sku": "OEM-BP-HC19",
    "name": "Ceramic Brake Pad Set Front",
    "description": "OEM-spec pads 2019-2021 Honda Civic",
    "make": "Honda",
    "model": "Civic",
    "year": "2019",
    "category": "brakes",
    "oem_brand": "Honda Genuine",
    "list_price": 89.5,
    "msrp": 112.0,
    "locations": {
      "L1": 12,
      "L2": 4,
      "L4": 8
    }
  }
]
```

CSV headers: `sku,name,description,make,model,year,category,oem_brand,list_price,msrp,qty_L1,qty_L2,...`

### Live HTTP feed

```bash
export OEM_FEED_URL="https://partner.example.com/v1/catalog"
export OEM_FEED_TOKEN="Bearer …"
parrts dms sync-oem --source http
# or API: POST /api/v1/dms/oem/sync {"source":"http"}
```

Without URL/token, HTTP adapter fails closed with a clear error — never invents OEM data.

## CLI

```bash
parrts dms seed              # synthetic OEM + locations
parrts dms sync-oem --source file --path data/oem/sample_oem_catalog.json
parrts dms status
parrts dms inventory
parrts dms reindex           # rebuild RAG from DMS catalog
```

## API (soft-loaded)

- `GET /api/v1/dms/status`
- `POST /api/v1/dms/seed`
- `POST /api/v1/dms/oem/sync`
- `GET /api/v1/dms/inventory`
- `GET /api/v1/dms/catalog`
- `GET|POST /api/v1/dms/customers`
- `GET|POST /api/v1/dms/orders`
- `POST /api/v1/dms/reindex`

Mutating routes respect `AUTH_MODE` / `require_user_if_production`.

## Roadmap to “full DMS + live OEM”

1. **Now (W13):** SQLite DMS core + adapters + UI  
2. **W14:** Postgres dual-mode + Alembic  
3. **W15:** Named OEM/distributor connectors under contract 📌  
4. **W16:** RO/accounting/GL bridges  
5. **W17:** Multi-tenant SaaS ops  

Illegal scraping of OEM portals is **out of scope forever**.
