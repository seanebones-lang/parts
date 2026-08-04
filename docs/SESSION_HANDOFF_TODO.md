# Parts — Session Handoff + Full TODO

**Updated:** 2026-08-04  
**Package:** `parrts` **v0.14.0**  
**Local SoT tree:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Ship remote (always):** https://github.com/seanebones-lang/parts (`origin` / `main`)  
**Legacy mirror:** https://github.com/seanebones-lang/Parrts-Dist-RAG (`legacy` remote)  
**CI:** must be green on `seanebones-lang/parts` before claiming done  

---

## 0. New session first actions

```bash
cd /Users/nexteleven/Desktop/Parrts-Dist-RAG
pwd && ls -la && git status
git fetch origin && git fetch legacy 2>/dev/null; git status -sb
git log --oneline -8
grep version pyproject.toml | head -1
gh run list -R seanebones-lang/parts -L 3
# Read: docs/SESSION_HANDOFF_TODO.md (this file) · docs/CTO_BACKLOG.md · docs/INSTALL.md
```

Load skill: `parrts-dist-rag-dev` + `direct-execution`.  
Ship path: orchestrator commits/pushes **parts** (and mirror `legacy` when user asks both repos).

---

## 1. Where we are (truth)

| Layer | Status | Notes |
|-------|--------|--------|
| Email desk G/Y/R + IMAP/SMTP human workflow | **Done** v0.8–0.9 | Selling point |
| Hybrid RAG counter search | **Done** | |
| DMS SQLite + Postgres dual-mode + Alembic | **Done** v0.10 | |
| Pay/ship UI key-gated Stripe/EasyPost | **Done** v0.11 | |
| Catalog admin + CSV, order lifecycle, invoice PDF | **Done** v0.12 | |
| JWT/RBAC + role mint | **Done** v0.13.1 | |
| Org + location ACL foundation | **Done** v0.13 | API + core |
| **Org / ACL operator UI** | **Done** v0.14.0 | `/orgs` + inventory filter |
| OEM Celery schedule helper | **Done** v0.13 | skips without URL |
| M1 single-site GA | **Closed** | |
| OEM beat in compose / staging keys | **Open** | Wave 24+ |
| Full multi-rooftop HA / partner OEM / RO-GL | **Open** | later |

**Tip commit at handoff write:** `03c3645` (Wave 23 org/ACL FE; package **v0.14.0**)  
**Remotes:** `origin` (parts) + `legacy` (Parrts-Dist-RAG) both match.

---

## 2. Full TODO (ordered for next sessions)

### Wave 21 — Green CI + handoff hygiene
- [x] CI green on parts
- [x] Dual-remote push hygiene
- [ ] Sync Desktop notes + Obsidian status cards

### Wave 22 — Auth JWT role mint E2E
- [x] All boxes

### Wave 23 — Org / ACL operator UI
- [x] FE page `/orgs`: list/create orgs
- [x] Assign location → org (`PUT /dms/locations/{code}/org`)
- [x] Edit user ACL (`PUT /dms/acl/{user_key}`)
- [x] Inventory page: optional `user_key` / `X-Parts-User` filter
- [x] Nav link + empty states when API down

### Wave 24 — OEM nightly beat + ops
- [ ] `docker-compose` / prod: Celery beat entry for `oem.scheduled_sync` (cron nightly)
- [ ] Env docs: `OEM_FEED_URL`, `OEM_FEED_TOKEN`, `OEM_SYNC_REINDEX`
- [ ] Smoke script step optional when URL set; skip clean when unset
- [ ] Log `oem_sync_runs` visible in status UI or CLI

### Wave 25 — Staging commerce happy path (keys required — fail closed)
- [ ] Stripe test key: order → PaymentIntent from Orders Pay
- [ ] EasyPost test key: rates + label from Shipping
- [ ] Email desk: IMAP/SMTP dry-run then real send in staging only
- [ ] One short runbook paragraph in INSTALL (no fake charges in demo)

### Wave 26 — M2 product depth
- [ ] Inter-store transfer workflow + stock conservation
- [ ] Manager approval threshold (hook RBAC)
- [ ] Observability baseline docs
- [ ] Load smoke numbers optional

### Wave 27 — M3 supply network (only with real partner)
- [ ] Feed scheduler watermark / delta
- [ ] SKU mapping UI vendor→internal
- [ ] One contracted connector sandbox (no scraping)

### Wave 28 — M4 commerce complete
- [ ] Pay invoice from order + webhook status
- [ ] Refund path
- [ ] Ship notice email via configured SMTP
- [ ] Analytics from real DMS events (not mock charts)

### Explicit non-goals
Unauthorized OEM scraping · CDK parity · fake Stripe/EasyPost/IMAP · blocking desk on GL/RO

---

## 3. Key paths

| Area | Path |
|------|------|
| Org FE | `frontend/app/orgs/page.tsx` |
| DMS client | `frontend/lib/dms-api.ts` |
| Inventory ACL filter | `frontend/app/inventory/page.tsx` |
| Nav | `frontend/app/navigation.tsx` |
| DMS API org/acl | `backend/app/api/v1/endpoints/dms.py` |
| Core ACL | `src/parrts/dms/service.py` |

---

## 4. Verify before any “done”

```bash
source .venv/bin/activate
ruff check src tests
PYTHONPATH=backend:src pytest -q tests/test_dms_api.py tests/test_rbac_org_acl.py
cd frontend && npm run type-check && npm run build
gh run list -R seanebones-lang/parts -L 1
git push origin main && git push legacy main
```

---

## 5. Cont command

> `cd ~/Desktop/Parrts-Dist-RAG && cont`  
> Read this file Wave 24+; OEM beat compose next.

*NextEleven LLC — Parts handoff.*
