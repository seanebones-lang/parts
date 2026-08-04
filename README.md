# Parts — Multi-Location Dealership System

**Repository:** https://github.com/seanebones-lang/parts  
**Owner:** NextEleven LLC  
**Package:** `parrts` v0.11.0  
**License:** Proprietary — NextEleven LLC (see `LICENSE`)

---

## What this is

**Parts** is NextEleven’s **dealership parts operating system**:

1. **Email desk (selling point)** — inbound parts questions auto-answered by section specialists, graded green/yellow/red, full-text searchable for staff  
2. **AI parts lookup** — hybrid dense + BM25 + RRF retrieval with green/yellow/red confidence  
3. **DMS core** — multi-location catalog, inventory, customers, orders (embedded SQLite; Postgres for multi-node)  
4. **OEM / distributor feeds** — pluggable ingest (`file` · `http` · synthetic for tests)  
5. **Enterprise API** — FastAPI `/api/v1` + specialist agents  
6. **Operator UI** — Next.js (email desk, search, inventory, orders, customers)  
7. **Ops** — Docker Compose (dev + prod), CI, eval harness  

```bash
python -m parrts email seed --clear
python -m parrts email status
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
```

See `docs/EMAIL_DESK.md`.
---

## System modes (all first-class)

| Mode | When | Storage |
|------|------|---------|
| **Embedded** | Single site / laptop / edge counter | SQLite `.parrts/dms.db` + local RAG index |
| **Server** | Multi-user dealership / multi-rooftop | Postgres (+ optional pgvector) + Redis |
| **OEM live** | `OEM_FEED_URL` (+ token) configured | HTTP adapter sync → DMS → reindex |

`AUTH_MODE=demo` is for **local open dev only**. Production deployments use `AUTH_MODE=production`, strong `SECRET_KEY`, `DEBUG=false`.

---

## Quick start

### Full local system

```bash
git clone https://github.com/seanebones-lang/parts.git
cd parts
./scripts/demo_up.sh          # ingest + DMS seed/reindex + API :8000 + UI :3000
# UI:  http://127.0.0.1:3000/parts
# API: http://127.0.0.1:8000/docs
./scripts/demo_smoke.sh
```

### CLI

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api]"
python -m parrts dms seed --reindex
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
parrts dms status
parrts dms inventory
```

### OEM feed (production path)

```bash
# File drop from distributor export
parrts dms sync-oem --source file --path /path/to/catalog.json --reindex

# Live HTTP feed
export OEM_FEED_URL="https://partner.example.com/v1/catalog"
export OEM_FEED_TOKEN="Bearer …"
parrts dms sync-oem --source http --reindex
```

### Production compose

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export AUTH_MODE=production DEBUG=false ENVIRONMENT=production
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Architecture

```
┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ Operator UI  │   │  CLI parrts │   │ OEM / files  │
│  Next.js     │   │  dms|query  │   │  HTTP feeds  │
└──────┬───────┘   └──────┬──────┘   └──────┬───────┘
       │                  │                 │
       ▼                  ▼                 ▼
┌───────────────────────────────────────────────────┐
│ FastAPI  /query  /api/v1/*  /api/v1/dms/*           │
└────────────┬───────────────────────┬──────────────┘
             ▼                       ▼
┌────────────────────┐   ┌──────────────────────────┐
│ parrts core (RAG)  │   │ DMS core (SQLite/PG path) │
│ hybrid + traffic   │◄──│ catalog · stock · orders  │
└────────────────────┘   └──────────────────────────┘
```

---

## Module status

| Module | Status |
|--------|--------|
| Parts search (AI) | **Production path** |
| DMS inventory / customers / orders | **Production path** (SQLite default; Postgres via `DMS_BACKEND=postgres` + migrate) |
| OEM ingest adapters | **Production path** (configure feed) |
| Auth JWT | **Production** when `AUTH_MODE=production` |
| Payments (Stripe) | **Production path when keyed** — `/payments` + `/api/v1/payments/order-intent` |
| Shipping (EasyPost) | **Production path when keyed** — `/shipping` + `/api/v1/shipping/rates|label` |
| Analytics / agents UI | **In product** — deepens with telemetry wiring |
| Multi-tenant SaaS billing | Roadmap |

Details: [`docs/SYSTEM.md`](docs/SYSTEM.md) · [`docs/DMS_OEM.md`](docs/DMS_OEM.md) · [`docs/ROADMAP_TO_COMPLETION.md`](docs/ROADMAP_TO_COMPLETION.md)

---

## Environment

Copy `.env.example` → `.env`.

| Variable | Production |
|----------|------------|
| `ENVIRONMENT` | `production` |
| `AUTH_MODE` | `production` |
| `SECRET_KEY` | strong random (required) |
| `DEBUG` | `false` |
| `POSTGRES_*` | required for multi-node |
| `OEM_FEED_URL` / `OEM_FEED_TOKEN` | when live feed is online |
| `STRIPE_*` / `EASYPOST_API_KEY` | when enabling pay/ship |

---

## Testing

```bash
pytest -q
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/eval_retrieval.py -k 5
cd frontend && npm run build
```

---

## License

Proprietary — NextEleven LLC. See `LICENSE`.
