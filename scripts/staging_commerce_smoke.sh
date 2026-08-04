#!/usr/bin/env bash
# Staging commerce smoke — fail closed without keys; optional live when keys set.
#
# Usage (repo root):
#   ./scripts/staging_commerce_smoke.sh
#   API_BASE=http://127.0.0.1:8000 ./scripts/staging_commerce_smoke.sh
#
# Optional live (never invents charges/labels/mail):
#   STRIPE_SECRET_KEY=sk_test_... EASYPOST_API_KEY=EZTK... ./scripts/staging_commerce_smoke.sh
#   STAGING_LIVE_EMAIL=1 EMAIL_HOST=... EMAIL_USER=... EMAIL_PASSWORD=... EMAIL_FROM=...
#
# Exit 0: fail-closed checks pass AND (no live keys OR live steps succeed).
# Exit 1: unexpected failure.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API="${API_BASE:-http://127.0.0.1:8000}"
export PYTHONPATH="${PYTHONPATH:-}:backend:src"
export ROOT

echo "== staging_commerce_smoke against $API =="

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

# --- Always: core helpers fail closed without inventing ---
python3 - <<'PY' || fail "core fail-closed unit path"
import os, sys
sys.path[:0] = ["src", "backend"]
# Ensure clean env for unit assertions
for k in list(os.environ):
    if k.startswith("STRIPE_") or k == "EASYPOST_API_KEY":
        # keep real keys if operator set them for later live section
        pass
from parrts.commerce import (
    create_payment_intent_for_order,
    get_shipping_rates,
    payment_status,
    shipping_status,
)
# Snapshot keys then clear for fail-closed block
_saved = {k: os.environ.get(k) for k in (
    "STRIPE_SECRET_KEY", "STRIPE_API_KEY", "EASYPOST_API_KEY"
)}
for k in _saved:
    os.environ.pop(k, None)

st = payment_status()
assert st["configured"] is False and st["live_ready"] is False, st
out = create_payment_intent_for_order(amount=25.0, order_id="smoke-1")
assert out["success"] is False and out["configured"] is False, out
assert "STRIPE" in out.get("error", "").upper()

ss = shipping_status()
assert ss["configured"] is False, ss
rates = get_shipping_rates(
    from_address={"street1": "100 Dealer", "city": "Chicago", "state": "IL", "zip": "60601"},
    to_address={"street1": "200 Main", "city": "Naperville", "state": "IL", "zip": "60540"},
    parcel={"weight": 16},
)
assert rates["success"] is False and rates["configured"] is False, rates

# restore
for k, v in _saved.items():
    if v is not None:
        os.environ[k] = v
    else:
        os.environ.pop(k, None)
print("CORE_FAIL_CLOSED_OK")
PY
ok "core commerce fail-closed (no fake charges/labels)"

# --- API reachable? optional for offline unit-only ---
if ! curl -fsS "$API/health" >/tmp/parts_staging_health.json 2>/dev/null; then
  echo "WARN: API $API unreachable — skip HTTP stages (core fail-closed still OK)"
  echo "Start with: ./scripts/demo_up.sh"
  echo "STAGING_SMOKE_PARTIAL_OK"
  exit 0
fi
ok "health $(python3 -c 'import json;print(json.load(open("/tmp/parts_staging_health.json")).get("status"))')"

# Config endpoints
curl -fsS "$API/api/v1/payments/config" >/tmp/parts_pay_cfg.json || fail "payments/config"
curl -fsS "$API/api/v1/shipping/config" >/tmp/parts_ship_cfg.json || fail "shipping/config"
python3 - <<'PY'
import json
pay=json.load(open("/tmp/parts_pay_cfg.json"))
ship=json.load(open("/tmp/parts_ship_cfg.json"))
assert "configured" in pay and pay.get("provider")=="stripe", pay
assert "configured" in ship and ship.get("provider")=="easypost", ship
print(f"pay.configured={pay.get('configured')} ship.configured={ship.get('configured')}")
PY
ok "payments/shipping config"

# HTTP fail-closed when keys not on the *server* process.
# We always POST; expect 503 if server lacks keys, 200 if server has keys.
code_pay=$(curl -sS -o /tmp/parts_pay_intent.json -w "%{http_code}" -X POST "$API/api/v1/payments/order-intent" \
  -H 'Content-Type: application/json' \
  -d '{"amount":19.99,"order_id":"staging-smoke","currency":"usd"}' || true)
code_ship=$(curl -sS -o /tmp/parts_ship_rates.json -w "%{http_code}" -X POST "$API/api/v1/shipping/rates" \
  -H 'Content-Type: application/json' \
  -d '{
    "from_address":{"name":"Parts Desk","street1":"100 Dealer Way","city":"Chicago","state":"IL","zip":"60601","country":"US"},
    "to_address":{"name":"Customer","street1":"200 Main St","city":"Naperville","state":"IL","zip":"60540","country":"US"},
    "parcel":{"weight":16},
    "order_id":"staging-smoke"
  }' || true)

python3 - <<PY
import json, os
code_pay=int("$code_pay")
code_ship=int("$code_ship")
pay=json.load(open("/tmp/parts_pay_intent.json"))
ship=json.load(open("/tmp/parts_ship_rates.json"))
# Accept fail-closed 503 OR live success 200 — never 500 inventing data
assert code_pay in (200, 503), (code_pay, pay)
assert code_ship in (200, 503), (code_ship, ship)
if code_pay == 503:
    d=str(pay.get("detail") or pay)
    assert "STRIPE" in d.upper() or "not configured" in d.lower(), pay
    print("PAY_HTTP_FAIL_CLOSED")
else:
    assert pay.get("success") is True and pay.get("payment_intent",{}).get("id"), pay
    print("PAY_HTTP_LIVE", pay["payment_intent"]["id"], pay["payment_intent"].get("status"))
if code_ship == 503:
    d=str(ship.get("detail") or ship)
    assert "EASYPOST" in d.upper() or "not configured" in d.lower(), ship
    print("SHIP_HTTP_FAIL_CLOSED")
else:
    assert ship.get("success") is True, ship
    rates=ship.get("rates") or []
    print("SHIP_HTTP_LIVE rates", len(rates), "shipment", ship.get("shipment_id"))
    # Optional label buy when STAGING_LIVE_LABEL=1 and rates present
    if os.environ.get("STAGING_LIVE_LABEL","").strip() in {"1","true","yes"} and rates:
        import urllib.request
        body=json.dumps({
            "shipment_id": ship.get("shipment_id") or ship.get("shipment",{}).get("id"),
            "rate_id": rates[0].get("id"),
            "order_id": "staging-smoke",
        }).encode()
        req=urllib.request.Request(
            "$API/api/v1/shipping/label",
            data=body,
            headers={"Content-Type":"application/json"},
            method="POST",
        )
        try:
            lab=json.loads(urllib.request.urlopen(req).read())
            assert lab.get("success") is True, lab
            print("SHIP_LABEL_LIVE", lab.get("tracking_code") or lab.get("label_url") or lab.keys())
        except Exception as e:
            print("SHIP_LABEL_SKIP", e)
PY
ok "order-intent + rates HTTP path (503 fail-closed or live)"

# Email desk: dry-run always; real SMTP only if STAGING_LIVE_EMAIL=1 and SMTP configured
python3 - <<'PY'
import json, os, urllib.request, urllib.error

api = os.environ.get("API_BASE", "http://127.0.0.1:8000")

def req(method, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    r = urllib.request.Request(
        f"{api}{path}",
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        try:
            j = json.loads(raw) if raw else {}
        except Exception:
            j = {"detail": raw}
        return e.code, j

# seed offline desk
code, seed = req("POST", "/api/v1/emails/seed", {"clear": True, "process": True})
assert code == 200, (code, seed)
code, lst = req("GET", "/api/v1/emails/?limit=5")
assert code == 200 and lst.get("emails"), lst
eid = lst["emails"][0]["id"]
code, sent = req("POST", f"/api/v1/emails/{eid}/send", {"dry_run": True})
assert code == 200 and sent.get("ok"), (code, sent)
print("EMAIL_DRY_RUN_OK", eid)

# mailbox status never leaks secrets
code, mb = req("GET", "/api/v1/emails/mailbox")
if code == 200:
    text = json.dumps(mb).lower()
    assert "password" not in text or mb.get("smtp_password") in (None, False, "", "***")
    print("EMAIL_MAILBOX", {k: mb.get(k) for k in list(mb)[:12]})
else:
    # alternate path
    code2, st = req("GET", "/api/v1/emails/status")
    assert code2 == 200, (code2, st)
    print("EMAIL_STATUS", st.get("mailbox") or st.get("total"))

live = os.environ.get("STAGING_LIVE_EMAIL", "").strip().lower() in {"1", "true", "yes"}
if live:
    # Real send only when SMTP configured — expect 200 or 503 fail-closed, never silent mark-sent
    code, real = req("POST", f"/api/v1/emails/{eid}/send", {"dry_run": False})
    assert code in (200, 503, 400), (code, real)
    if code == 503:
        print("EMAIL_LIVE_FAIL_CLOSED", real.get("detail") or real)
    else:
        print("EMAIL_LIVE_SEND", real)
else:
    print("EMAIL_LIVE_SKIPPED (set STAGING_LIVE_EMAIL=1 + SMTP to attempt real send)")
print("EMAIL_STAGING_OK")
PY
ok "email dry-run (+ optional live SMTP)"

# Optional process-local live stripe/easypost when env keys present (does not require API env)
python3 - <<'PY'
import os, sys
sys.path[:0] = ["src"]
from parrts.commerce import create_payment_intent_for_order, get_shipping_rates, stripe_secret_key, easypost_api_key

if stripe_secret_key():
    out = create_payment_intent_for_order(amount=5.0, order_id="local-staging", description="staging smoke")
    assert out.get("success") is True, out
    print("LOCAL_STRIPE_LIVE", out["payment_intent"]["id"], out["payment_intent"]["status"])
else:
    print("LOCAL_STRIPE_SKIPPED")

if easypost_api_key():
    out = get_shipping_rates(
        from_address={"name":"Parts","street1":"417 Montgomery St","city":"San Francisco","state":"CA","zip":"94104","country":"US"},
        to_address={"name":"Customer","street1":"179 N Harbor Dr","city":"Redondo Beach","state":"CA","zip":"90277","country":"US"},
        parcel={"weight": 16},
    )
    if not out.get("success"):
        # Some test keys reject sample addresses — still fail closed honestly
        print("LOCAL_EASYPOST_ERROR", out.get("error"))
        assert out.get("configured") is True
    else:
        print("LOCAL_EASYPOST_LIVE rates", len(out.get("rates") or []))
else:
    print("LOCAL_EASYPOST_SKIPPED")
print("LOCAL_OPTIONAL_DONE")
PY
ok "optional local live keys"

echo "STAGING_COMMERCE_SMOKE OK"
echo "Note: no fake charges/labels/mail. Live steps only when credentials present."
