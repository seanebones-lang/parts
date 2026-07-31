# Parts — CTO Backlog

**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.6.1**  
**Honesty:** `[x]` only after measured verify.

## Is the system complete?

| Definition | Status |
|------------|--------|
| **Pilot-complete** (dealer room demo: AI search + DMS ops + OEM ingest path) | **YES (W13.1)** |
| Full DMS replacement (CDK/Reynolds parity) | **NO** — multi-quarter (W14–W17) |
| Live OEM with manufacturer contracts | **NO** until feed URL/token + contracts |

## Wave 13 — DMS + OEM (done)
- [x] Offline DMS SQLite core + CLI + API + FE Live modules
- [x] OEM synthetic/file/http adapters
- [x] Auth demo mode offline-safe

## Wave 13.1 — Pilot completeness (this ship)
- [x] CI: core ignores TestClient DMS API; backend-smoke runs dms_api + auth + seed/reindex
- [x] CLI: `parrts dms reindex` + `customers`
- [x] demo_up seeds DMS + reindexes RAG
- [x] E2E: seed --reindex → query returns **OEM-*** SKUs
- [x] greenlet/httpx in backend requirements

## Later (not “incomplete pilot”)
- W14 Postgres dual-mode + Alembic  
- W15 Named OEM connectors 📌 contracts  
- W16 RO / accounting  
- W17 Multi-tenant SaaS  

## Never
Unauthorized OEM scraping · claiming full DMS GA without the product work
