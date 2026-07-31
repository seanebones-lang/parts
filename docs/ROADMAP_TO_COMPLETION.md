# Parts — Full Roadmap to Completion

**Product:** Parts by NextEleven LLC  
**Repo:** https://github.com/seanebones-lang/parts  
**Local:** `~/Desktop/Parrts-Dist-RAG`  
**Package:** `parrts` (current line: v0.7.x)  
**Document status:** Living roadmap — update checkboxes only after measured delivery  
**Last updated:** 2026-07-31

---

## 1. North star (definition of done)

Parts is the **dealership parts operating system** for multi-location dealers:

| Capability | Done means |
|------------|------------|
| Counter AI search | Staff type natural language; ranked SKUs across rooftops; green/yellow/red confidence; human confirms |
| DMS | Catalog, multi-location inventory, customers, orders, transfers, reserves — production data store |
| OEM / distributor feeds | Scheduled live sync from authorized file/HTTP/partner APIs; fail closed; audit log |
| Operator UI | Day-to-day ops without needing a second DMS for core parts workflows |
| Integrations | Stripe + EasyPost + email when configured; no fake charges/labels |
| Deploy | Single-site embedded **and** multi-user server (Postgres) with production auth |
| Ops | Backups, migrations, monitoring, CI green, runbooks |

**Out of scope forever**

- Unauthorized scraping of OEM portals  
- Claiming CDK / Reynolds / Tekion full feature parity without building those surfaces  
- Silent hallucinated OEM catalog rows  

---

## 2. Current baseline (shipped)

### Done — treat as the real product foundation

| Area | What’s live |
|------|-------------|
| **AI core** | `src/parrts` hybrid dense + BM25 + RRF, traffic-light policy, parent expand, CLI/API query |
| **Eval** | Offline harness; default dataset high hit@k |
| **DMS core** | SQLite embedded (`.parrts/dms.db`): catalog, inventory, customers, orders, stock reserve |
| **OEM adapters** | `synthetic` (bootstrap/tests), `file` (JSON/CSV), `http` (`OEM_FEED_URL` + token) |
| **Bridge** | `parrts dms seed\|sync-oem --reindex` → rebuild RAG from DMS |
| **API** | FastAPI `/`, `/health`, `/query`, `/demo/scenarios`, `/api/v1/*` (16+ routers incl. `dms`, `system`) |
| **Auth** | `AUTH_MODE=demo\|production`; production secret guard; JWT on mutating routes in production |
| **UI** | Next.js: Parts Search, Inventory, Orders, Customers; Payments/Shipping key-gated modules |
| **Ops** | `system_up/down/smoke`, prod compose, CI matrix, honest docs (`SYSTEM.md`, `DMS_OEM.md`) |

### Partial / integration-gated

| Area | Gap |
|------|-----|
| Payments | Service code exists; UI reports key status; end-to-end pay-from-order UX incomplete |
| Shipping | Same — EasyPost when keyed; label-from-order UX incomplete |
| Agents UI | LangGraph specialists exist offline; not full SLA/ops console |
| Analytics | Module shell; not bound to full telemetry warehouse |
| Postgres DMS | Enterprise models/services exist; **DMS SoT today is SQLite embedded** |

---

## 3. Completion phases

### Phase A — Production single-site GA (target: complete the *system* for one rooftop / small multi-location)

**Goal:** A dealer can run Parts as their parts system without a second primary DMS for catalog/stock/orders/search.

| ID | Work | Acceptance |
|----|------|------------|
| A1 | **Postgres dual-mode DMS** — same API; `DMS_BACKEND=sqlite\|postgres` | E2E seed/order on both backends; no SQLite required in prod compose |
| A2 | **Alembic migrations** for server schema | `alembic upgrade head` on empty PG; no `create_all` as prod path |
| A3 | **Catalog admin UI** — create/edit SKU, bulk import CSV in UI | Import 1k rows; appears in inventory + search after reindex |
| A4 | **Transfers** — location A → B with audit | Stock conserved; API + UI |
| A5 | **Receiving / adjust stock** | Adjust reason codes; immutable audit trail |
| A6 | **Order lifecycle** — open → pick → invoice → complete/cancel | Status machine + stock release on cancel |
| A7 | **Invoices PDF** from order | Downloadable PDF; stored path |
| A8 | **User roles** — counter / manager / admin | RBAC on mutating routes |
| A9 | **Backup/restore runbook** | Documented + scripted backup of DMS + `.parrts` |
| A10 | **Production install guide** | One doc: env, compose, first feed, first user, SSL notes |
| A11 | **Hardening** | Rate limits on auth; disable public `/docs` in prod; CORS allowlist only |
| A12 | **CI green on main** as merge gate always | All jobs required; no soft-fail on core tests |

**Exit criteria Phase A**

- [ ] Fresh prod compose → create admin → import feed → search → order → invoice  
- [ ] `AUTH_MODE=production` end-to-end with real JWT  
- [ ] Backup/restore drill documented and run once  
- [ ] No “pilot/demo” language in product UI  

---

### Phase B — Multi-location enterprise (target: multi-rooftop server)

| ID | Work | Acceptance |
|----|------|------------|
| B1 | Multi-tenant **org** + locations under org | Data isolation tests |
| B2 | Location permissions per user | Counter only sees assigned stores |
| B3 | Inter-store transfer workflow + approvals | Manager approve threshold |
| B4 | Central catalog + local overrides (price/qty) | Override wins at location |
| B5 | Replication / HA Postgres notes (or managed PG) | Runbook |
| B6 | Observability — structured logs, metrics, error tracking | Dashboards or documented stack |
| B7 | Performance — p95 search & order under load target | Load test numbers checked in |
| B8 | SSO optional (OIDC) | Login with dealer IdP |

**Exit criteria Phase B**

- [ ] 3+ locations, 5+ users, role isolation proven  
- [ ] Load test baseline published in `docs/`  

---

### Phase C — Live OEM / distributor network

| ID | Work | Acceptance |
|----|------|------------|
| C1 | Feed scheduler (cron/celery) — nightly + on-demand | Sync runs logged in `oem_sync_runs` |
| C2 | Mapping UI — vendor SKU → internal SKU | Conflict resolution |
| C3 | Partner connector pack (contracted only) | At least one real partner sandbox |
| C4 | Delta sync + watermark | No full reload required daily |
| C5 | Price effective dates / supersession chains | Superseded SKU redirects in search |
| C6 | VIN / EPC optional enrichment (licensed data only) | Feature-flagged |

**Exit criteria Phase C**

- [ ] One live authorized feed in production for a design customer  
- [ ] Fail-closed behavior monitored (alerts on sync fail)  

---

### Phase D — Full ops suite (payments, shipping, comms, agents)

| ID | Work | Acceptance |
|----|------|------------|
| D1 | Pay invoice from order (Stripe) | Real test-mode charge; webhook updates status |
| D2 | Refund / partial refund | Ledger consistent |
| D3 | Ship order (EasyPost) rates + label | Label PDF; tracking stored |
| D4 | Email: quote / invoice / ship notice | Delivered via configured SMTP/provider |
| D5 | Agents console — invoke specialists with audit | Correlation ID per run |
| D6 | Analytics warehouse (orders, fill rate, dead stock) | Dashboard from real DMS events |
| D7 | Barcode / serialized (existing modules) wired to DMS stock | Scan adjust qty |

**Exit criteria Phase D**

- [ ] Order → pay → ship → email happy path in staging with test keys  
- [ ] Analytics from real events not mock charts  

---

### Phase E — Market completeness / scale

| ID | Work | Acceptance |
|----|------|------------|
| E1 | Mobile-responsive counter PWA | Usable on tablet at parts counter |
| E2 | Offline queue queue (edge) | Queue orders when API brief outage |
| E3 | Multi-currency / tax hooks | Configurable |
| E4 | Compliance pack — audit export, retention | Export last 90 days |
| E5 | App marketplace / plugins (optional) | Documented extension points |
| E6 | SLA, support tiers, status page | Business ops |

---

## 4. Recommended sequencing (critical path)

```
A1 Postgres DMS dual-mode
A2 Alembic
A3 Catalog admin + CSV UI
A6 Order lifecycle
A8 Roles
A10 Install guide
A11 Hardening
    ↓
B1–B3 multi-location enterprise
    ↓
C1–C3 live feed ops
    ↓
D1–D4 pay/ship/email
    ↓
E* scale & polish
```

Do **not** block A on full OEM partner deals — file/HTTP adapters already carry real catalogs.

---

## 5. Milestone checklist (completion board)

### M0 — Product identity (done)
- [x] Parts framed as the system (not pilot shell)  
- [x] Core search + embedded DMS + OEM adapters + UI  

### M1 — Single-site production GA
- [ ] Postgres DMS dual-mode  
- [ ] Migrations  
- [ ] Catalog admin  
- [ ] Full order lifecycle + invoice PDF  
- [ ] RBAC  
- [ ] Prod install + backup runbooks  
- [ ] CI required green  

### M2 — Multi-rooftop enterprise
- [ ] Org model + location ACL  
- [ ] Transfers + approvals  
- [ ] Observability + load baseline  

### M3 — Live supply network
- [ ] Scheduled feeds  
- [ ] One contracted connector in prod  
- [ ] Supersession / mapping  

### M4 — Commerce complete
- [ ] Stripe order pay + webhooks  
- [ ] EasyPost labels  
- [ ] Customer email notifications  
- [ ] Real analytics  

### M5 — Scale complete
- [ ] PWA counter  
- [ ] Compliance export  
- [ ] Support/SLA packaging  

**“Roadmap complete”** = M1–M4 shipped and verified for at least one production dealer; M5 as growth.

---

## 6. Workstream ownership (for agent waves)

| Stream | Owns | Primary paths |
|--------|------|----------------|
| **CORE** | RAG + DMS SQLite/logic | `src/parrts/**` |
| **BE** | API, auth, PG, integrations | `backend/**` |
| **FE** | Operator UI | `frontend/**` |
| **OPS** | Compose, CI, runbooks, backups | `scripts/**`, `.github/**`, `docs/**` |
| **DATA** | Feeds, mapping, quality | `data/oem/**`, feed jobs |

Agents: non-overlapping paths; orchestrator integrates, tests, pushes `seanebones-lang/parts`.

---

## 7. Verification gates (every phase)

```bash
# Always
ruff check src tests
pytest -q
PYTHONPATH=backend:src python scripts/verify_boot.py
python scripts/eval_retrieval.py -k 5
cd frontend && npm run build

# System
./scripts/system_up.sh && ./scripts/system_smoke.sh

# DMS / OEM
parrts dms status
parrts dms seed --reindex   # or real sync-oem
parrts query "…" --no-llm
```

CI: `gh run list -R seanebones-lang/parts -L 1` must be **success** before calling a milestone done.

---

## 8. Risk register

| Risk | Mitigation |
|------|------------|
| OEM data licensing | Contracts only; fail closed; no scraping |
| Dual storage drift (SQLite vs PG) | Single service interface; one backend active per deploy |
| Scope creep to full DMS accounting | Keep GL/RO in Phase D/E; don’t block M1 |
| Auth misconfig in prod | Boot guard on weak secrets; checklist in install guide |
| Search quality on real catalogs | Eval harness + dealer query logs → golden set |

---

## 9. Immediate next sprint (start here)

1. **A1/A2** — Postgres backend for `DmsService` + Alembic  
2. **A3** — Catalog admin + CSV upload UI  
3. **A6** — Order status machine  
4. **A8** — Roles  
5. **A10/A11** — Install guide + prod hardening  

Ship target after that sprint: **M1 candidate** (single-site production GA).

---

## 10. Related docs

| Doc | Purpose |
|-----|---------|
| `docs/SYSTEM.md` | Product definition |
| `docs/DMS_OEM.md` | DMS + feed ops |
| `docs/DEALERSHIP_PITCH.md` | Operator brief |
| `docs/CTO_BACKLOG.md` | Execution checkboxes (short) |
| `docs/DEMO_WALKTHROUGH.md` | Bring-up commands |
| This file | **Full roadmap to completion** |

---

*NextEleven LLC — Parts roadmap. Update only with measured ships to `origin/main`.*
