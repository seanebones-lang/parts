# DMS + OEM feeds

**Package:** `parrts` v0.20.0 · Product SoT: `docs/SYSTEM.md`

## Role

The DMS core **is** the inventory and order system for Parts. SQLite embedded and Postgres server are deployment choices, not “demo vs real.”

## Storage

| Deploy | Path |
|--------|------|
| Embedded (default) | `.parrts/dms.db` — `DMS_BACKEND=sqlite` |
| Server | Postgres — `DMS_BACKEND=postgres` + `DMS_DATABASE_URL` |

```bash
export DMS_BACKEND=postgres
export DMS_DATABASE_URL=postgresql://postgres:***@localhost:5432/dealership_parts
parrts dms migrate
parrts dms --backend postgres status
```

Alembic: `alembic.ini` + `src/parrts/dms/migrations/`. Soft schema also adds tables/columns on `ensure_schema()` (transfers, adjustments, supersessions, payment_events, shipment_events, order payment/ship stamps).

## Tables (embedded / dual-mode)

| Area | Tables / notes |
|------|----------------|
| Core | `locations`, `catalog_parts`, `inventory_levels`, `customers`, `orders`, `order_lines` |
| OEM | `oem_sync_runs` |
| Org | `orgs`, `user_location_acl`, `locations.org_id` |
| Transfers | `stock_transfers` (+ manager approval threshold) |
| Adjust | `stock_adjustments` (immutable audit) |
| Supersession | `part_supersessions` (cycle-safe resolve) |
| Commerce ledger | `payment_events`, `shipment_events` |
| Order stamps | `payment_status`, `last_payment_id`, `paid_amount`, `ship_status`, `tracking_code`, `last_shipment_id` |

## OEM adapters

| Adapter | Use |
|---------|-----|
| `file` | Distributor/OEM export (JSON or CSV) |
| `http` | Live feed — `OEM_FEED_URL` + optional `OEM_FEED_TOKEN` |
| `synthetic` | Tests / empty-box bootstrap only |

HTTP **fails closed** if network/feed unavailable. No silent invented OEM rows. **No portal scraping.**

### Commands

```bash
parrts dms seed --reindex
parrts dms sync-oem --source file --path catalog.json --reindex
parrts dms sync-oem --source http --reindex
parrts dms status
parrts dms analytics
parrts dms inventory
parrts dms reindex
parrts dms supersede OLD NEW --notes "..."
parrts dms resolve-sku OLD
parrts dms supersessions
parrts dms export-audit --days 90 --out audit.json
parrts dms oem-runs
parrts dms set-status ORDER_ID picking|invoiced|completed|cancelled
parrts dms invoice ORDER_ID
```

### API (selected)

- `GET /api/v1/dms/status` · `GET /api/v1/dms/analytics`
- `POST /api/v1/dms/oem/sync` · `GET /api/v1/dms/oem/runs`
- `GET|POST /api/v1/dms/inventory` · `POST …/inventory/adjust` · `GET …/adjustments`
- `GET|POST /api/v1/dms/catalog` · CSV import
- `GET|POST /api/v1/dms/customers` · `orders` · lifecycle `PATCH …/status` · invoice
- `GET|POST /api/v1/dms/transfers*`
- `GET|POST /api/v1/dms/supersessions` · `GET …/resolve` · `DELETE …/{old_sku}`
- `GET /api/v1/dms/payments/events` · `POST …/orders/{id}/payment-events`
- `GET /api/v1/dms/shipments/events`
- `GET /api/v1/dms/compliance/export?days=90`
- `POST /api/v1/dms/reindex`

Commerce (key-gated, separate routers):

- `POST /api/v1/payments/order-intent` — records DMS payment ledger when `order_id` int  
- `POST /api/v1/shipping/rates` · `POST /api/v1/shipping/label` — shipment ledger when `order_id` int  

Mutations respect production JWT + RBAC (`catalog.supersession`, `compliance.export`, `inventory.adjust`, `transfers.approve`, …).

## UI

`/inventory` · `/orders` · `/customers` · `/transfers` · `/analytics` · `/supersessions` · `/catalog` · `/orgs` · `/payments` · `/shipping`
