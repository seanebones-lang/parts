# Parts — Multi-Location Dealership System

**Repository:** https://github.com/seanebones-lang/parts  
**Owner:** NextEleven LLC  
**Package:** `parrts` **v0.22.0**  
**Tip track:** `git log -1` on `main` (ship remote `origin`)  
**License:** Proprietary — NextEleven LLC (see `LICENSE`)  
**Next session:** [`docs/SESSION_HANDOFF_TODO.md`](docs/SESSION_HANDOFF_TODO.md) · CTO: [`docs/CTO_BACKLOG.md`](docs/CTO_BACKLOG.md)

---

## What this is

**Parts** is NextEleven’s **dealership parts operating system**:

1. **Email desk (selling point)** — inbound parts questions auto-answered by section specialists, graded green/yellow/red, human approve/send, IMAP/SMTP when keyed  
2. **AI parts lookup** — hybrid dense + BM25 + RRF with green/yellow/red confidence + optional parent expand / supersession notes  
3. **DMS core** — multi-location catalog, inventory, customers, orders, transfers, stock receive/adjust, supersessions  
4. **AI workflow automation** — run ledger, HIL alerts, email→order bridge, results desk (`/results`)  
5. **OEM / distributor feeds** — pluggable ingest (`file` · `http` · synthetic for tests); Celery beat when URL set  
6. **Commerce ledgers** — Stripe payment intents + EasyPost rates/labels **when keyed**; DMS `payment_events` / `shipment_events` (fail closed, no fake charges/labels)  
7. **Operator UI** — Next.js (email, search, catalog, inventory, orders, customers, orgs, transfers, analytics, supersessions, automation results, payments, shipping)  
8. **Counter resilience** — offline mutation queue (create order/customer) + light PWA shell (manifest + SW; never caches API JSON)  
9. **Ops** — Docker Compose (dev + prod), CI, eval harness, backup scripts  

```bash
python -m parrts email seed --clear && python -m parrts email status
python -m parrts dms seed --reindex
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
python -m parrts dms analytics
python -m parrts automation results
python -m parrts dms notify 1 --kind order_status --dry-run   # needs customer email on order
python -m parrts dms notifications --limit 20
python scripts/load_baseline.py   # writes docs/LOAD_BASELINE.md
```

See `docs/EMAIL_DESK.md` · `docs/SYSTEM.md` · `docs/DMS_OEM.md` · `docs/AUTOMATION.md` · `docs/LOAD_BASELINE.md`.

---

## System modes (all first-class)

| Mode | When | Storage |
|------|------|---------|
| **Embedded** | Single site / laptop / edge counter | SQLite `.parrts/dms.db` + local RAG index |
| **Server** | Multi-user / multi-rooftop | Postgres (`DMS_BACKEND=postgres`) + Redis |
| **OEM live** | `OEM_FEED_URL` (+ token) configured | HTTP adapter sync → DMS → reindex |

`AUTH_MODE=demo` is for **local open dev only**. Production: `AUTH_MODE=production`, strong `SECRET_KEY`, `DEBUG=false`.

---

## Quick start

### Full local system

```bash
git clone https://github.com/seanebones-lang/parts.git
cd parts
./scripts/demo_up.sh          # ingest + DMS seed/reindex + email seed + API :8000 + UI :3000
# UI:  http://127.0.0.1:3000/emails  (selling point)
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
parrts dms analytics
parrts dms supersessions
parrts dms export-audit --days 90 --out /tmp/parts-audit.json
parrts automation status
parrts automation results
parrts dms notify ORDER_ID --kind order_status --dry-run
parrts dms notifications
```

### OEM feed (production path)

```bash
parrts dms sync-oem --source file --path /path/to/catalog.json --reindex

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
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│ Operator UI  │   │  CLI parrts      │   │ OEM / files  │
│  Next.js     │   │  dms|email|auto  │   │  HTTP feeds  │
│  + offline Q │   │  query|notify…  │   │              │
└──────┬───────┘   └────────┬─────────┘   └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────┐
│ FastAPI  /query  /api/v1/{dms,emails,automation}/*       │
└────────────┬───────────────────────────┬─────────────────┘
             ▼                           ▼
┌────────────────────┐   ┌─────────────────────────────────┐
│ parrts core (RAG)  │   │ DMS + notify + automation        │
│ hybrid + traffic   │◄──│ catalog · stock · orders · SS    │
│ supersession notes │   │ pay/ship/notify ledgers · HIL    │
└────────────────────┘   └─────────────────────────────────┘
```

---

## Module status (honest)

| Module | Status |
|--------|--------|
| Email desk | **Production-ready** (live mailbox when IMAP/SMTP set) |
| Parts search (AI) | **Production path** |
| DMS inventory / customers / orders / transfers / adjust | **In system** |
| Supersession chains | **In system** (`/supersessions`, CLI, query meta) |
| Live DMS analytics | **In system** (`/analytics` — real tables only) |
| OEM ingest adapters | **Production path** (configure feed; no scrape) |
| Auth JWT + RBAC | **Production** when `AUTH_MODE=production` |
| Payments (Stripe) | **When keyed** + DMS payment ledger |
| Shipping (EasyPost) | **When keyed** + DMS shipment ledger |
| Offline queue / light PWA | **In system** (W31 — orders/customers queue; shell SW) |
| AI workflow automation | **In system** (W32 — runs · HIL · email→order · `/results`) |
| Customer notify | **In system** (W33 — `notification_events` · dry-run default · SMTP when keyed) |
| Load baseline | **Measured offline** (`docs/LOAD_BASELINE.md` — not prod SLA) |
| Partner OEM connector pack | **Contract only** — not claimed live without feed |
| Full CDK/Reynolds parity | **No** |
| Multi-tenant SaaS billing | Roadmap |

Contact: **hello@mothership-ai.com** · [mothership-ai.com](https://mothership-ai.com)

Details: [`docs/SYSTEM.md`](docs/SYSTEM.md) · [`docs/DMS_OEM.md`](docs/DMS_OEM.md) · [`docs/AUTOMATION.md`](docs/AUTOMATION.md) · [`docs/ROADMAP_TO_COMPLETION.md`](docs/ROADMAP_TO_COMPLETION.md) · [`docs/ROADMAP.md`](docs/ROADMAP.md)

---

## Environment

Copy `.env.example` → `.env`.

| Variable | Production |
|----------|------------|
| `ENVIRONMENT` | `production` |
| `AUTH_MODE` | `production` |
| `SECRET_KEY` | strong random (required) |
| `DEBUG` | `false` |
| `POSTGRES_*` / `DMS_BACKEND` | multi-node |
| `OEM_FEED_URL` / `OEM_FEED_TOKEN` | live feed |
| `STRIPE_*` / `EASYPOST_API_KEY` | pay/ship |
| `IMAP_*` / `EMAIL_*` | live mailbox + customer notify SMTP |
| `PARRTS_NOTIFY_ON_STATUS` | default on — dry-run notify on status change when email present |
| `PARRTS_AUTO_NOTIFY` | live SMTP notify only when true **and** SMTP configured |

---

## Testing

```bash
# from repo root
ruff check src tests
pytest -q --tb=short \
  --ignore=tests/test_backend_boot.py \
  --ignore=tests/test_auth_demo_mode.py \
  --ignore=tests/test_agents_mocked.py \
  --ignore=tests/test_langgraph_workflow.py \
  --ignore=tests/test_pgvector_e2e.py \
  --ignore=tests/test_dms_api.py \
  --ignore=tests/test_email_api.py
PYTHONPATH=backend:src python scripts/verify_boot.py
PYTHONPATH=backend:src pytest -q tests/test_dms_api.py tests/test_email_api.py tests/test_backend_boot.py
python scripts/eval_retrieval.py -k 5   # expect mode=parrts, high hit@5
cd frontend && npm run type-check && npm run build
gh run list -R seanebones-lang/parts -L 1   # presentable = success
```

---

## License

Proprietary — NextEleven LLC. See `LICENSE`.
