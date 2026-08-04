# Parts — the system

**Parts** is the dealership parts system (NextEleven LLC). Not a trial UI around a demo catalog.

## Product surfaces

| Surface | Role |
|---------|------|
| **Email desk** | Inbound parts email → specialists → green/yellow/red → searchable archive |
| Counter search | Natural language → ranked SKUs + traffic light |
| DMS | Catalog, multi-location stock, customers, orders |
| OEM feeds | File / HTTP ingest into DMS, then RAG reindex |
| API | FastAPI for UI, integrations, automation |
| Integrations | Stripe / EasyPost activate with credentials |

## Runtime profiles

### Embedded (default local install)

- SQLite DMS at `.parrts/dms.db` (`DMS_BACKEND=sqlite`)
- Local vector/BM25 index under `.parrts/index/`
- Suitable for single-rooftop or edge workstation

### Multi-user server

- Postgres DMS: `DMS_BACKEND=postgres` + `DMS_DATABASE_URL` (or `POSTGRES_*`)
- Schema: `parrts dms migrate` (Alembic `001_dms_core`) — also auto `CREATE TABLE IF NOT EXISTS` on first use
- Compose stack: Postgres (+ Redis) via `docker-compose.prod.yml`
- `AUTH_MODE=production`, strong `SECRET_KEY`, `DEBUG=false`
- Same application code; different storage/ops profile

### OEM live

- Set `OEM_FEED_URL` and optional `OEM_FEED_TOKEN`
- `parrts dms sync-oem --source http --reindex`
- No silent fake OEM data if the feed is down

## Operator entry points

```bash
./scripts/demo_up.sh                 # bring system up locally
parrts dms seed --reindex            # baseline catalog (or replace with real feed)
parrts dms sync-oem --source file --path dealer_export.json --reindex
```

UI:

- `/emails` — inbound email desk (selling point: auto-answer + G/Y/R + search)  
- `/parts` — counter search  
- `/inventory` — stock by location  
- `/orders` — order capture + reserve  
- `/customers` — customer master  

```bash
parrts email seed --clear
parrts email status
```

See `docs/EMAIL_DESK.md`.

## Security

- Production must not run with default secrets (boot guard enforces this).
- Mutating APIs require JWT when `AUTH_MODE=production`.
- Demo auth is only for open local development.

## What “done” means for the product

The system is the parts + DMS + feed platform. Continuous expansion:

- Deeper OEM partner connectors under contract  
- Postgres dual-write / multi-site replication  
- RO / accounting bridges  
- Payments & shipping when keys are present  

Unauthorized scraping of OEM portals is out of scope.
