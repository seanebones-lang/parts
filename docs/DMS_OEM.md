# DMS + OEM feeds

## Role in the product

The DMS core **is** the inventory and order system for Parts. SQLite embedded mode and Postgres server mode are deployment choices, not “demo vs real.”

## Storage

| Deploy | Path |
|--------|------|
| Embedded (default) | `.parrts/dms.db` (stdlib sqlite3) — `DMS_BACKEND=sqlite` |
| Server | Postgres — `DMS_BACKEND=postgres` + `DMS_DATABASE_URL` (or `POSTGRES_*`) |

### Postgres dual-mode

```bash
export DMS_BACKEND=postgres
export DMS_DATABASE_URL=postgresql://postgres:pass@localhost:5432/dealership_parts
# one-time schema
parrts dms migrate                 # alembic upgrade head (001_dms_core)
# or ensure_schema() on first DmsService use also CREATE TABLE IF NOT EXISTS
parrts dms --backend postgres status
parrts dms --backend postgres seed --reindex
```

Same `DmsService` API and `/api/v1/dms/*` routes — backend is env-selected.  
Alembic lives at `alembic.ini` + `src/parrts/dms/migrations/`.

## OEM adapters (production)

| Adapter | Use |
|---------|-----|
| `file` | Distributor/OEM export (JSON or CSV) |
| `http` | Live feed — `OEM_FEED_URL` + optional `OEM_FEED_TOKEN` |
| `synthetic` | Automated tests and empty-box bootstrap only |

### JSON feed shape

```json
[
  {
    "sku": "OEM-BP-HC19",
    "name": "Ceramic Brake Pad Set Front",
    "description": "Pads 2019-2021 Honda Civic",
    "make": "Honda",
    "model": "Civic",
    "year": "2019",
    "category": "brakes",
    "oem_brand": "Honda Genuine",
    "list_price": 89.5,
    "msrp": 112.0,
    "locations": { "L1": 12, "L2": 4, "L4": 8 }
  }
]
```

### Commands

```bash
parrts dms seed --reindex                 # bootstrap sample if no feed yet
parrts dms sync-oem --source file --path catalog.json --reindex
parrts dms sync-oem --source http --reindex
parrts dms status
parrts dms inventory
parrts dms reindex                        # rebuild AI index from DMS
```

### API

- `GET /api/v1/dms/status`
- `POST /api/v1/dms/oem/sync`
- `GET /api/v1/dms/inventory`
- `GET /api/v1/dms/catalog`
- `GET|POST /api/v1/dms/customers`
- `GET|POST /api/v1/dms/orders`
- `POST /api/v1/dms/reindex`

Mutations respect `AUTH_MODE=production` JWT.

## Live feed failure policy

HTTP adapter **fails closed** with a clear error if the network/feed is unavailable. It does not invent OEM rows.

Unauthorized scraping of OEM portals is permanently out of scope.
