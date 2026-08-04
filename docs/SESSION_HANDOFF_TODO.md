# Parts — Session Handoff + Full TODO

**Updated:** 2026-08-04  
**Package:** `parrts` **v0.14.1**  
**Local SoT tree:** `/Users/nexteleven/Desktop/Parrts-Dist-RAG`  
**Ship remote:** https://github.com/seanebones-lang/parts (`origin` / `main`)  
**Legacy mirror:** https://github.com/seanebones-lang/Parrts-Dist-RAG  

---

## 0. New session first actions

```bash
cd /Users/nexteleven/Desktop/Parrts-Dist-RAG
git fetch origin && git status -sb && git log --oneline -5
grep version pyproject.toml | head -1
gh run list -R seanebones-lang/parts -L 2
# Read this file · docs/CTO_BACKLOG.md · docs/INSTALL.md
```

Load: `parrts-dist-rag-dev` + `direct-execution`.

---

## 1. Where we are

| Layer | Status |
|-------|--------|
| Email desk | Done |
| DMS + commerce + JWT mint | Done |
| Org/ACL FE `/orgs` | Done v0.14.0 |
| **OEM Celery beat nightly** | **Done v0.14.1** |
| Staging pay/ship keys | Open Wave 25 |
| Multi-rooftop HA / partner OEM | Later |

**Tip:** `8c34388` / `c395ef2` Wave 24 OEM beat v0.14.1  
**Remotes:** origin + legacy match.
---

## 2. TODO

### Waves 21–24
- [x] CI hygiene, JWT mint, org FE, OEM beat compose

### Wave 25 — Staging commerce happy path (keys required — fail closed)
- [ ] Stripe test key: order → PaymentIntent from Orders Pay
- [ ] EasyPost test key: rates + label from Shipping
- [ ] Email desk: IMAP/SMTP dry-run then real send in staging only
- [ ] One short runbook paragraph in INSTALL (no fake charges in demo)

### Wave 26 — M2 product depth
- [ ] Inter-store transfer + stock conservation
- [ ] Manager approval threshold (RBAC)
- [ ] Observability baseline docs

### Wave 27–28
Partner OEM / full commerce (see prior handoff)

### Non-goals
OEM scraping · CDK parity · fake Stripe/EasyPost/IMAP

---

## 3. Key paths (Wave 24)

| Area | Path |
|------|------|
| Beat schedule | `backend/app/celery.py` (`oem-scheduled-sync-nightly`) |
| Task | `backend/app/tasks/oem_tasks.py` |
| Runs list | `parrts dms oem-runs` · `GET /api/v1/dms/oem/runs` |
| Status | `svc.status()` → `oem_sync_runs` |
| Compose | `docker-compose.yml` full profile · `docker-compose.prod.yml` celery+beat |

---

## 4. Cont

> Wave 25 staging keys only with real test credentials — fail closed otherwise.

*NextEleven LLC*
