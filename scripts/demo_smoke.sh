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
# allow string traffic_light or nested
if not color and isinstance(d.get("traffic_light"), str):
    color=d["traffic_light"]
print(f"hits={len(hits)} traffic_light={color!r} top={hits[0].get('sku') or hits[0].get('name')}")
assert len(hits)>=1
print("SMOKE OK")
PY
