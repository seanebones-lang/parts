# Parts — Session Handoff + Full TODO

**Updated:** 2026-08-04  
**Package:** `parrts` **v0.13.1**  
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
| DMS SQLite + Postgres dual-mode + Alembic | **Done** v0.10 | `DMS_BACKEND`, `parrts dms migrate` |
| Pay/ship UI key-gated Stripe/EasyPost | **Done** v0.11 | Fail closed |
| Catalog admin + CSV, order lifecycle, invoice PDF | **Done** v0.12 | M1 residual |
| Install + backup/restore scripts | **Done** v0.12 | `docs/INSTALL.md` |
| JWT/RBAC `require_permission` | **Done** v0.13 | X-Parts-Role demo; User.role prod |
| Org + location ACL foundation | **Done** v0.13 | tables + inventory filter |
| OEM Celery schedule helper | **Done** v0.13 | skips without `OEM_FEED_URL` |
| **JWT role mint on login/refresh** | **Done** v0.13.1 | `role` + `parts_role` claims |
| **M1 single-site GA checklist** | **Closed** | |
| M2 FE org UI / beat schedule | **Open** | Wave 23+ |
| Full multi-rooftop HA / partner OEM / RO-GL | **Open** | later |

**Tip commit at handoff write:** `afd98b3` (Wave 22 JWT role mint; package **v0.13.1**)  
**Remotes:** `origin` (parts) + `legacy` (Parrts-Dist-RAG) both match.  
**Desktop/parts:** full tree @ same SHA as SoT.

---

## 2. Full TODO (ordered for next sessions)

### Wave 21 — Green CI + handoff hygiene (do first if red)
- [x] Confirm `gh run list -R seanebones-lang/parts -L 1` = **success**
- [x] Core pytest has **no** bare `@pytest.mark.asyncio` without plugin (use `asyncio.run` or backend-smoke only)
- [x] Push `main` to **origin/parts** and **legacy/Parrts-Dist-RAG**
- [ ] Sync Desktop notes + Obsidian status cards

### Wave 22 — Auth JWT role mint E2E
- [x] On login/token create: put `role` (or `parts_role`) in JWT claims from `User.role`
- [x] Map `user|manager|admin|superuser` via `parrts.rbac.map_app_role`
- [x] Production path: mutating DMS routes 403 for counter on seed/import (measured)
- [x] Demo path still open with default admin; `X-Parts-Role: counter` still 403 seed
- [x] Doc: INSTALL § roles with curl examples stay accurate

### Wave 23 — Org / ACL operator UI
- [ ] FE page `/orgs` or section under settings: list/create orgs
- [ ] Assign location → org (`PUT /dms/locations/{code}/org`)
- [ ] Edit user ACL (`PUT /dms/acl/{user_key}`)
- [ ] Inventory page: optional `X-Parts-User` / user_key filter in UI
- [ ] Nav link + empty states when API down

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
- [ ] Observability: structured request logs + basic metrics already partially present — document baseline
- [ ] Load smoke numbers optional (document p95 target later)

### Wave 27 — M3 supply network (only with real partner)
- [ ] Feed scheduler watermark / delta (beyond full replace)
- [ ] SKU mapping UI vendor→internal
- [ ] One contracted connector sandbox (no scraping)

### Wave 28 — M4 commerce complete
- [ ] Pay invoice from order + webhook status
- [ ] Refund path
- [ ] Ship notice email via configured SMTP
- [ ] Analytics from real DMS events (not mock charts)

### Explicit non-goals (do not start)
- Unauthorized OEM portal scraping  
- Claiming CDK/Reynolds parity  
- Fake Stripe/EasyPost/IMAP without credentials  
- Blocking desk on multi-quarter GL/RO  

---

## 3. Key paths (do not thrash)

| Area | Path |
|------|------|
| Core DMS | `src/parrts/dms/` |
| RBAC | `src/parrts/rbac.py` |
| Auth JWT mint | `backend/app/services/auth_service.py` (`create_access_token_for_user`) |
| Auth endpoints | `backend/app/api/v1/endpoints/auth.py` |
| Commerce | `src/parrts/commerce.py` |
| Email desk | `src/parrts/email/` |
| Auth deps | `backend/app/api/deps.py` |
| DMS API | `backend/app/api/v1/endpoints/dms.py` |
| OEM task | `backend/app/tasks/oem_tasks.py` |
| FE | `frontend/app/{emails,catalog,orders,payments,shipping}/` |
| Docs | `docs/CTO_BACKLOG.md`, `INSTALL.md`, this file |

---

## 4. Verify before any “done”

```bash
source .venv/bin/activate
ruff check src tests
PYTHONPATH=src:backend pytest -q \
  --ignore=tests/test_backend_boot.py \
  --ignore=tests/test_auth_demo_mode.py \
  --ignore=tests/test_agents_mocked.py \
  --ignore=tests/test_langgraph_workflow.py \
  --ignore=tests/test_pgvector_e2e.py \
  --ignore=tests/test_dms_api.py \
  --ignore=tests/test_email_api.py \
  --ignore=tests/test_commerce_api.py
PYTHONPATH=backend:src pytest -q tests/test_backend_boot.py tests/test_dms_api.py \
  tests/test_email_api.py tests/test_auth_demo_mode.py tests/test_commerce_api.py tests/test_rbac_org_acl.py
PYTHONPATH=backend:src python scripts/verify_boot.py
cd frontend && npm run type-check && npm run build
gh run list -R seanebones-lang/parts -L 1
```

Push:

```bash
git push origin main
git push legacy main   # mirror Parrts-Dist-RAG
```

---

## 5. Sync map (Desktop + Obsidian + vault)

| Location | Role |
|----------|------|
| `~/Desktop/Parrts-Dist-RAG` | **Engineering SoT** — edit here only |
| `~/Desktop/parts` | Thin/stale clone — refresh from `origin/parts` or ignore for eng |
| `~/Desktop/parts docs/` | Sales packet (not eng SoT) |
| `~/Desktop/Sean-GitHub-Vault/Repos/parts.md` + `Parrts-Dist-RAG.md` | Vault cards → ship URL **parts** |
| `~/Documents/Obsidian Vault/Parts-Status.md` | Human status + link to this handoff |
| GitHub `seanebones-lang/parts` | Ship |
| GitHub `seanebones-lang/Parrts-Dist-RAG` | Legacy mirror of same `main` when pushed |

---

## 6. Cont command for next agent

> `cd ~/Desktop/Parrts-Dist-RAG && cont`  
> Read `docs/SESSION_HANDOFF_TODO.md` Wave 23+; execute next open eng boxes; pytest + push **parts** (+ legacy if dual-ship).

*NextEleven LLC — Parts handoff. Update checkboxes only after measured ship.*
