# TEAM UPDATE — Docs wave (honesty sync to v0.20.0)

**Date:** 2026-08-05  
**Tip:** `e29a10c` · package **v0.20.0** · CI green on main  
**Ship:** https://github.com/seanebones-lang/parts  

## Why

Docs lagged engineering (README still said v0.15; ROADMAP stuck at W13). Specialized docs pass aligned product narrative to measured ship through **Wave 31**.

## Current product state (one screen)

| Layer | State |
|-------|--------|
| Email desk | Production-ready selling point |
| Hybrid RAG + traffic light | Production path |
| DMS (SQLite default / PG dual-mode) | Inventory, orders lifecycle, transfers, stock adjust |
| Supersession | Core + API + FE `/supersessions` |
| Analytics | Live from DMS tables only |
| Pay / ship | Key-gated providers + DMS ledgers (fail closed) |
| Offline / PWA | Order/customer queue + shell SW + install prompt |
| Partner OEM / HA / CDK parity | **Not** claimed |

## Docs touched

- `README.md`, `docs/SYSTEM.md`, `docs/ROADMAP.md`, `docs/ROADMAP_TO_COMPLETION.md` (baseline/milestones)
- `docs/AGENTS.md`, `docs/DMS_OEM.md`, `docs/INSTALL.md` (header/surfaces)
- `docs/OBSERVABILITY.md`, `docs/DEALERSHIP_PITCH.md`, `docs/DEMO_WALKTHROUGH.md`
- `docs/TEAM_UPDATE_DOCS_v0.20.0.md` (this file)
- Vault `Parts-Status` cards when present

## Verify before dealer walk

```bash
gh run list -R seanebones-lang/parts -L 1   # success
grep version pyproject.toml                 # 0.20.0
```

## Next eng

Partner OEM only with contract · multi-tenant/load · HA/RO-GL later.
