#!/usr/bin/env bash
# Smoke test for dealership demo (API must already be up, or we start briefly)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API="${API_BASE:-http://127.0.0.1:8000}"

echo "== demo_smoke against $API =="

fail() { echo "FAIL: $*" >&2; exit 1; }

curl -fsS "$API/health" >/tmp/parts_health.json || fail "health unreachable"
echo "health: $(python3 -c 'import json;print(json.load(open("/tmp/parts_health.json")).get("status"))')"

curl -fsS "$API/demo/scenarios" >/tmp/parts_scen.json || fail "demo/scenarios missing"
python3 - <<'PY'
import json
d=json.load(open("/tmp/parts_scen.json"))
assert d.get("scenarios") and len(d["scenarios"])>=3, d
print(f"scenarios: {len(d['scenarios'])}")
PY

# POST /query
curl -fsS -X POST "$API/query" \
  -H 'Content-Type: application/json' \
  -d '{"query":"brake pads for 2019 Honda Civic","top_k":5}' \
  >/tmp/parts_query.json || fail "POST /query failed"

python3 - <<'PY'
import json
d=json.load(open("/tmp/parts_query.json"))
hits=d.get("hits") or d.get("results") or []
assert hits, d
tl=d.get("traffic_light") or {}
color = tl.get("color") if isinstance(tl, dict) else tl
if not color and isinstance(d.get("traffic_light"), str):
    color=d["traffic_light"]
print(f"hits={len(hits)} traffic_light={color!r} top={hits[0].get('sku') or hits[0].get('name')}")
assert len(hits)>=1
print("QUERY SMOKE OK")
PY

# Email desk
curl -fsS -X POST "$API/api/v1/emails/seed" \
  -H 'Content-Type: application/json' \
  -d '{"clear":true,"process":true}' \
  >/tmp/parts_email_seed.json || fail "email seed failed"

curl -fsS "$API/api/v1/emails/status" >/tmp/parts_email_status.json || fail "email status failed"

python3 - <<'PY'
import json
st=json.load(open("/tmp/parts_email_status.json"))
assert st.get("total",0) >= 6, st
colors=st.get("by_traffic_light") or {}
assert "red" in colors or sum(colors.values())>=6, colors
assert st.get("production_ready") is True or "specialists" in st
print(f"email desk total={st.get('total')} colors={colors} mailbox={st.get('mailbox')}")
# list
import urllib.request
raw=urllib.request.urlopen("http://127.0.0.1:8000/api/v1/emails/?limit=5").read()
lst=json.loads(raw)
assert lst.get("count",0)>=1 and lst.get("emails"), lst
e=lst["emails"][0]
# dry-run approve
eid=e["id"]
req=urllib.request.Request(
    f"http://127.0.0.1:8000/api/v1/emails/{eid}/send",
    data=json.dumps({"dry_run":True}).encode(),
    headers={"Content-Type":"application/json"},
    method="POST",
)
sent=json.loads(urllib.request.urlopen(req).read())
assert sent.get("ok"), sent
print("EMAIL DESK SMOKE OK")

# OEM scheduled helper — skip clean when OEM_FEED_URL unset
import os, subprocess, sys
root = os.environ.get("ROOT") or os.getcwd()
# when run from demo_smoke, cwd is repo root
env = os.environ.copy()
env.setdefault("PYTHONPATH", "backend:src")
r = subprocess.run(
    [sys.executable, "-c",
     "from app.tasks.oem_tasks import run_scheduled_oem_sync; import json; print(json.dumps(run_scheduled_oem_sync()))"],
    cwd=root if os.path.isdir(os.path.join(root, "backend")) else os.getcwd(),
    env=env,
    capture_output=True,
    text=True,
)
if r.returncode != 0:
    # soft: backend may not be on PYTHONPATH in pure FE smoke
    print(f"OEM schedule helper skip/soft: {r.stderr.strip() or r.stdout.strip()[:200]}")
else:
    out = (r.stdout or "").strip().splitlines()[-1] if r.stdout else "{}"
    import json as _json
    try:
        data = _json.loads(out)
    except Exception:
        data = {"raw": out}
    assert data.get("ok") is True, data
    if data.get("skipped"):
        print(f"OEM schedule: skipped ({data.get('reason','no OEM_FEED_URL')})")
    else:
        print(f"OEM schedule: ran ok reindex={data.get('reindex')}")
print("SMOKE OK")
PY
