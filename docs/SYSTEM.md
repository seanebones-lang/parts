# Parts — the system

**Parts** by NextEleven LLC — dealership parts operating system.  
**Package:** `parrts` **v0.22.0** · Ship: https://github.com/seanebones-lang/parts  
**SoT clone:** `~/Desktop/Parrts-Dist-RAG` · Handoff: `docs/SESSION_HANDOFF_TODO.md`  
**Brand:** white-label **NextEleven Parts** only — no dealer co-brand in product UI/docs.  
**Contact:** hello@mothership-ai.com · mothership-ai.com

## Product surfaces

| Surface | Role | Status |
|---------|------|--------|
| **Email desk** | Inbound → specialists → G/Y/R → human approve/send · FTS archive | Production-ready |
| Counter search | NL → ranked SKUs + traffic light (+ supersession notes when DMS present) | Production path |
| DMS | Catalog, multi-location stock, customers, orders, transfers, receive/adjust | In system |
| Supersessions | Old SKU → current chain; FE `/supersessions` | In system |
| Analytics | Real DMS counts, order-book $, dead stock, fill-rate proxy | In system (not mock charts) |
| **Automation** | Runs ledger · HIL alerts · email→order · rulesets · `/results` | **Wave 32** shipped |
| **Customer notify** | Order/pay/ship/invoice drafts + `notification_events`; SMTP when keyed | **Wave 33** shipped |
| **Load baseline** | Offline measured timings → `docs/LOAD_BASELINE.md` | **Wave 33** (not prod SLA) |
| OEM feeds | File / HTTP ingest → DMS → reindex; nightly beat when URL set | Adapters ready; live needs credentials |
| Commerce | Stripe intents + EasyPost rates/labels when keyed; DMS pay/ship ledgers | Fail closed without keys |
| Offline / PWA | Queue create order/customer offline; installable shell SW | **Wave 31** shipped |
| API | FastAPI `/`, `/health`, `/query`, `/api/v1/*` | Soft-loaded routers (dms, emails, automation, …) |
| Integrations | Stripe / EasyPost / IMAP-SMTP activate with credentials only | No invented delivery |

## Runtime profiles

### Embedded (default local)

- SQLite DMS `.parrts/dms.db` (`DMS_BACKEND=sqlite`)
- Email desk `.parrts/emails.db`
- Automation `.parrts/automation.db` + rulesets `.parrts/rulesets.json`
- Local vector/BM25 under `.parrts/index/`
- Single-rooftop / edge workstation

### Multi-user server

- Postgres DMS: `DMS_BACKEND=postgres` + `DMS_DATABASE_URL`
- `parrts dms migrate` (Alembic) + auto `CREATE TABLE IF NOT EXISTS`
- Compose: `docker-compose.prod.yml`
- `AUTH_MODE=production`, strong `SECRET_KEY`, `DEBUG=false`

### OEM live

- `OEM_FEED_URL` + optional `OEM_FEED_TOKEN`
- `parrts dms sync-oem --source http --reindex`
- Fail closed if feed down — **no silent fake OEM rows**
- Partner connectors only under contract (not scraped portals)

## Operator entry points

```bash
./scripts/demo_up.sh
parrts dms seed --reindex
parrts email seed --clear
parrts dms analytics
parrts dms supersessions
parrts automation results
parrts dms notify ORDER_ID --kind order_status --dry-run
parrts dms notifications
python scripts/load_baseline.py
```

| UI path | Module |
|---------|--------|
| `/emails` | Email desk (selling point) + email→order bridge |
| `/parts` | Counter AI search |
| `/catalog` | Catalog admin |
| `/inventory` | Stock + receive/adjust |
| `/orders` | Lifecycle + pay/ship badges + **Notify** (dry-run) |
| `/customers` | Customer master |
| `/orgs` | Org / location ACL |
| `/transfers` | Inter-store transfers |
| `/analytics` | Live DMS analytics |
| `/supersessions` | SKU supersession maps |
| `/results` | Automation results (runs · HIL alerts) |
| `/payments` | Stripe (keyed) + order prefill |
| `/shipping` | EasyPost (keyed) + order prefill |

## CLI surfaces (selected)

| Command | Role |
|---------|------|
| `parrts automation status\|results\|runs\|alerts\|resolve\|rulesets\|email-to-order` | W32 automation |
| `parrts dms notify\|notifications` | W33 customer notify ledger |
| `parrts email *` | Desk G/Y/R + mailbox |
| `parrts dms *` | Catalog, stock, orders, OEM, compliance, … |
| `parrts query` | Hybrid RAG counter path |

## API surfaces (selected)

| Path | Role |
|------|------|
| `/api/v1/automation/*` | status, results, runs, alerts, rulesets, email→order |
| `POST /api/v1/dms/orders/{id}/notify` | Customer notify (dry-run default) |
| `GET /api/v1/dms/notifications` | Notification ledger |
| `/api/v1/emails/*` | Email desk |
| `/api/v1/dms/*` | DMS ops |

## Security

- Production boot guard rejects weak `SECRET_KEY` / `DEBUG=true`
- Mutating APIs: JWT when `AUTH_MODE=production`
- RBAC: counter / manager / admin (`X-Parts-Role` in demo; JWT `role`+`parts_role` in prod)
- Demo auth is open local desk only
- Customer notify: dry-run default; live SMTP only with credentials + confirm / `PARRTS_AUTO_NOTIFY`

## Honesty / non-claims

| Claim | Truth |
|-------|--------|
| Email desk production-ready | **Yes** (v0.9.0+) |
| Automation MIN + `/results` | **Yes** (W32 / v0.22.0+) |
| Customer notify ledger | **Yes** (W33 / v0.22.0) — delivery only when SMTP keyed |
| Full CDK / Reynolds parity | **No** |
| Live OEM without feed credentials | **No** |
| Live Stripe/EasyPost without keys | **No** — idle + ledger may record fail-closed attempts |
| Analytics from mock charts | **No** — `/api/v1/dms/analytics` only |
| Dealer co-brand (any third-party dealership) | **No** — NextEleven Parts white-label only |

## Continuous expansion (not blocking pilot)

- Contracted OEM partner connectors  
- Multi-site HA / RO-GL bridges  
- SSO (OIDC)  
- Deeper offline (beyond order/customer queue)  
- Full multi-user load / SLA packaging  

Unauthorized OEM portal scraping is **out of scope forever**.
