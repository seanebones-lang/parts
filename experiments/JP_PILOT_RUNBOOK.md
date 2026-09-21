# JP Transmission — Pilot Runbook (internal controlled pilot)

**Product is feature-frozen for this window.** This runbook is measurement + environment only.

Repo: `Parrts-Dist-RAG` · Branch: `vertical/transmission-hard-parts`  
Pilot DB is **isolated** — never the default developer `.parrts/dms.db`.

| Concept | Path / value |
|---------|----------------|
| Suggested pilot root | `<repo>/.pilot/jp` |
| SQLite DMS | `<pilot-root>/.parrts/dms.db` |
| Real telemetry source | `jp_real_pilot` |
| Demo/test sources | `jp_demo` · `test` |
| Env (backend) | `PARRTS_ROOT` · `PARRTS_VERTICAL=transmission` · `JP_PILOT_MODE=real` · `COUNTER_TELEMETRY_SOURCE=jp_real_pilot` |
| Env (frontend) | `NEXT_PUBLIC_DEMO_VERTICAL=transmission` · `NEXT_PUBLIC_JP_PILOT_MODE=real` |

Production RBAC / public deploy: **BLOCKED**. This is a laptop/internal pilot only.

---

## A. Bootstrap isolated pilot DB

```bash
cd /path/to/Parrts-Dist-RAG
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python \
  scripts/bootstrap_jp_pilot.py --root "$(pwd)/.pilot/jp" --reset
```

- Creates schema, baseline demo seed, commits `data/jp_demo/jp_demo_inventory_seed.csv`
- Refuses overwrite without `--reset`; `--reset` takes a timestamped backup first
- Prints representative search modes + `jp_real_pilot sessions: 0`

## B. Start backend (real pilot telemetry)

```bash
export PARRTS_ROOT="$(pwd)/.pilot/jp"
export PARRTS_VERTICAL=transmission
export JP_PILOT_MODE=real
export COUNTER_TELEMETRY_SOURCE=jp_real_pilot
export AUTH_MODE=demo ENVIRONMENT=development DEBUG=true
export JEV_DECISION_ENABLED=0
PYTHONPATH="$(pwd)/backend:$(pwd)/src" /tmp/phase4-integrated-venv/bin/python \
  -m uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

## C. Start frontend (JP transmission)

```bash
cd frontend
NEXT_PUBLIC_DEMO_VERTICAL=transmission \
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 \
NEXT_PUBLIC_JP_PILOT_MODE=real \
npm run dev -- -p 3000 -H 127.0.0.1
```

Restart FE after changing any `NEXT_PUBLIC_*` var.

**Email Desk inventory authority:** with `PARRTS_VERTICAL=transmission`, email specialists use **DMS + counter_search only**. They must **never** fall back to legacy PartsRAGEngine / Civic brake pads. If transmission inventory cannot answer → human review.

## Email demo reseed (pre-pilot only)

Only when **no real JP emails** exist and real pilot counter count is still 0:

```bash
export PARRTS_ROOT="$(pwd)/.pilot/jp"
export PARRTS_VERTICAL=transmission
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python <<'PY'
from parrts.email.service import EmailService
from pathlib import Path
root = Path(".pilot/jp").resolve()
svc = EmailService(root=root, vertical="transmission")
# refuse if non-demo message_ids appear
rows = svc.list(limit=500)
realish = [r for r in rows if not str(r.get("message_id") or "").startswith("tx-demo-")]
assert not realish, f"refusing clear — non-demo emails: {realish[:3]}"
print(svc.seed_demo(clear=True, process=True, vertical="transmission"))
PY
```

## D. Health

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:3000/ | head -c 200
# JP shell: open http://127.0.0.1:3000/transmission
```

## E. One TEST/demo query (must not count as real pilot)

```bash
# Backend still on pilot root is OK — force demo source:
curl -sS -X POST http://127.0.0.1:8000/api/v1/dms/transmission/inquiry \
  -H 'Content-Type: application/json' \
  -d '{"query":"6L80 pump","telemetry_source":"jp_demo"}' | python3 -m json.tool | head
```

Or temporarily:

```bash
export COUNTER_TELEMETRY_SOURCE=jp_demo
# restart API, run one search, then restore jp_real_pilot
```

Confirm report still shows **0** real finalized:

```bash
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python \
  scripts/report_jp_pilot.py --root "$(pwd)/.pilot/jp"
```

## F. Real pilot mode

Keep B+C env with `JP_PILOT_MODE=real` / `COUNTER_TELEMETRY_SOURCE=jp_real_pilot` / `NEXT_PUBLIC_JP_PILOT_MODE=real`.

Operator flow:

1. Parts Search → enter real counter wording unchanged  
2. **exact_match** → Accept / Correct (UoW feedback finalizes session)  
3. **inventory_matches** → pick physical lot → Quote or Reserve (selection finalizes session)  
4. **needs_review** → Resolve request with final SKU (finalizes session)  

A plain search with no action is **not** finalized and does **not** count toward 50.

## G. Export pilot report

```bash
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python \
  scripts/report_jp_pilot.py --root "$(pwd)/.pilot/jp" \
  --csv "$(pwd)/.pilot/jp/pilot_export.csv" --json
```

Progress line looks like: `17 / 50 finalized real requests`  
Do **not** claim 50 until finalized real count is 50.  
Do **not** compute one “overall accuracy” mixing discovery browse with exact resolver truth.

## H. Stop services

Ctrl-C API and FE processes (or kill ports 8000/3000).

## I. Backup pilot DB

```bash
cp -a "$(pwd)/.pilot/jp/.parrts/dms.db" \
  "$(pwd)/.pilot/jp/.parrts/dms.db.bak.$(date -u +%Y%m%dT%H%M%SZ)"
```

---

## Telemetry rules (short)

| Mode | Finalized when |
|------|----------------|
| exact_match | UoW **ACCEPT** or **CORRECT** |
| needs_review | UoW **RESOLVE** |
| inventory_matches | Lot **ADD_TO_QUOTE** or **RESERVE** recorded |

Sources: only `jp_real_pilot` rows appear in the real pilot report.  
Offline evals (`answer_transmission_inquiry` / bare `counter_search`) do **not** write pilot sessions.

## Honesty notes

- Type classification for this synthetic pilot: **catalog name + SKU convention** (no authoritative structured `catalog_parts.part_type` column in discovery).  
- CONTROLLED INTERNAL PILOT: supported · PUBLIC/PRODUCTION: blocked on RBAC + deploy.
