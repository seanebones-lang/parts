# Parts (parrts) — CTO Backlog

**Root:** monorepo clone of `seanebones-lang/parts`  
**Ship:** https://github.com/seanebones-lang/parts (`origin` / `main`)  
**Package:** `parrts` **v0.5.1** (Wave 12)  
**SoT:** this file. `[x]` only after measured verification.

Waves 0–11 complete (CI green, prod hardening, presentable tree).

---

## Truth: can we present to a dealership *today*?

| Claim | Reality |
|-------|---------|
| Multi-location NL parts search | **Yes** — hybrid RAG + traffic-light |
| Live API `/query` without Postgres | **Yes** |
| Parts UI with live path | **Yes** — `/parts` + demo_up |
| Full DMS / payments / shipping GA | **No** — roadmap previews |
| One-command dealer demo | **Yes** — `./scripts/demo_up.sh` (Wave 12) |

**Positioning:** Design-partner **pilot** — not “replace your DMS tomorrow.”

---

## Wave 12 — Dealership demo-ready

### Demo ops
- [x] W12.1 `scripts/demo_up.sh`
- [x] W12.2 `scripts/demo_smoke.sh` (+ demo_down.sh)
- [x] W12.3 `docs/DEALERSHIP_PITCH.md`
- [x] W12.4 `docs/DEMO_WALKTHROUGH.md` updated

### Backend demo surface
- [x] W12.5 `GET /demo/scenarios`
- [x] W12.6 CORS includes 127.0.0.1:3000; `/query` traffic_light

### Frontend honesty + polish
- [x] W12.7 Home: pilot banner + CTA Parts Search (no fake live revenue)
- [x] W12.8 Nav: Parts Search first; Preview labels
- [x] W12.9 Stub pages → `RoadmapPreview`
- [x] W12.10 Parts: scenario chips + auto-search + location line

### Verify & ship
- [x] W12.11 Live smoke: demo_up + demo_smoke **SMOKE OK** (hits=5, traffic green)
- [x] W12.12 pytest 67p, next build, push

## Explicit non-goals Wave 12
Live Stripe · multi-tenant SSO · real OEM catalog · 13-agent SLA claims
