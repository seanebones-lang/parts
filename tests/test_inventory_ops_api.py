"""API-level tests for /api/v1/dms/ops/* inventory + quote routes."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_MODE", "demo")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ["JEV_DECISION_ENABLED"] = "0"

from app.api.v1.endpoints.dms import get_dms_service  # noqa: E402
from backend.main import app  # noqa: E402
from parrts.dms.service import DmsService  # noqa: E402
from parrts.transmission.seed_loader import load_demo_seed  # noqa: E402


@pytest.fixture()
def client():
    tmp = TemporaryDirectory()
    root = Path(tmp.name)

    boot = DmsService(root)
    boot.ensure_schema()
    load_demo_seed(boot)
    boot.store.close()

    def _svc():
        return DmsService(root)

    app.dependency_overrides[get_dms_service] = _svc
    with TestClient(app) as c:
        yield c, root
    app.dependency_overrides.clear()
    tmp.cleanup()


def test_api_receive_adjust_transfer_reserve_release(client):
    c, _ = client
    r = c.post(
        "/api/v1/dms/ops/receive",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 5, "idempotency_key": "api-recv-1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["on_hand"] >= 5

    r2 = c.post(
        "/api/v1/dms/ops/receive",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 5, "idempotency_key": "api-recv-1"},
    )
    assert r2.status_code == 200
    assert r2.json().get("idempotent") is True

    bad = c.post(
        "/api/v1/dms/ops/receive",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 0},
    )
    assert bad.status_code in (400, 422)

    adj = c.post(
        "/api/v1/dms/ops/adjust",
        json={
            "sku": "6L80-PUMP-01",
            "location": "CHI-N",
            "delta": 1,
            "reason": "found",
            "idempotency_key": "api-adj-1",
        },
    )
    assert adj.status_code == 200, adj.text

    xfer = c.post(
        "/api/v1/dms/ops/transfer",
        json={
            "sku": "6L80-PUMP-01",
            "from_location": "CHI-N",
            "to_location": "OHARE",
            "qty": 1,
            "idempotency_key": "api-xfer-1",
        },
    )
    assert xfer.status_code == 200, xfer.text

    res = c.post(
        "/api/v1/dms/ops/reserve",
        json={
            "sku": "6L80-PUMP-01",
            "location": "CHI-N",
            "qty": 1,
            "idempotency_key": "api-res-1",
        },
    )
    assert res.status_code == 200, res.text
    rid = res.json()["reservation_id"]

    over = c.post(
        "/api/v1/dms/ops/reserve",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 99999},
    )
    assert over.status_code == 409, over.text
    assert "available" in over.json()["detail"].lower() or "attempted" in over.json()["detail"].lower()

    rel = c.post(f"/api/v1/dms/ops/reservations/{rid}/release")
    assert rel.status_code == 200, rel.text
    rel2 = c.post(f"/api/v1/dms/ops/reservations/{rid}/release")
    assert rel2.status_code == 409


def test_api_quote_order_flow(client):
    c, _ = client
    c.post("/api/v1/dms/ops/receive", json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 5})
    q = c.post("/api/v1/dms/ops/quotes", json={"customer_label": "API Shop"})
    assert q.status_code == 200, q.text
    qid = q.json()["id"]

    line = c.post(
        f"/api/v1/dms/ops/quotes/{qid}/lines",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 1, "unit_price_cents": 24500},
    )
    assert line.status_code == 200, line.text
    lid = line.json()["lines"][0]["id"]

    upd = c.patch(
        f"/api/v1/dms/ops/quotes/{qid}/lines/{lid}",
        json={"qty": 2, "unit_price_cents": 20000},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["lines"][0]["qty"] == 2

    # second line
    line2 = c.post(
        f"/api/v1/dms/ops/quotes/{qid}/lines",
        json={"sku": "6L80-VB-01", "location": "CHI-N", "qty": 1, "unit_price_cents": 10000},
    )
    assert line2.status_code == 200, line2.text
    assert len(line2.json()["lines"]) == 2

    # shrink pump line back to 1 before reserve
    c.patch(f"/api/v1/dms/ops/quotes/{qid}/lines/{lid}", json={"qty": 1})

    rsv = c.post(f"/api/v1/dms/ops/quotes/{qid}/reserve")
    assert rsv.status_code == 200, rsv.text
    assert rsv.json()["status"] == "reserved"

    # cannot edit reserved
    bad = c.patch(f"/api/v1/dms/ops/quotes/{qid}/lines/{lid}", json={"qty": 3})
    assert bad.status_code == 409

    order = c.post(f"/api/v1/dms/ops/quotes/{qid}/convert")
    assert order.status_code == 200, order.text
    oid = order.json()["id"]
    assert order.json()["status"] == "open"

    done = c.post(f"/api/v1/dms/ops/orders/{oid}/complete")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"

    # double complete idempotent
    done2 = c.post(f"/api/v1/dms/ops/orders/{oid}/complete")
    assert done2.status_code == 200
    assert done2.json().get("idempotent") is True or done2.json()["status"] == "completed"


def test_api_invalid_sku_location(client):
    c, _ = client
    bad_sku = c.post(
        "/api/v1/dms/ops/receive",
        json={"sku": "NO-SUCH-SKU", "location": "CHI-N", "qty": 1},
    )
    assert bad_sku.status_code in (400, 404, 422, 409)

    bad_loc = c.post(
        "/api/v1/dms/ops/receive",
        json={"sku": "6L80-PUMP-01", "location": "NOWHERE-ZZZ", "qty": 1},
    )
    assert bad_loc.status_code in (400, 404, 422, 409)


def test_api_cancel_quote(client):
    c, _ = client
    c.post("/api/v1/dms/ops/receive", json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 3})
    q = c.post("/api/v1/dms/ops/quotes", json={"customer_label": "Cancel me"}).json()
    c.post(
        f"/api/v1/dms/ops/quotes/{q['id']}/lines",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 1},
    )
    c.post(f"/api/v1/dms/ops/quotes/{q['id']}/reserve")
    can = c.post(f"/api/v1/dms/ops/quotes/{q['id']}/cancel")
    assert can.status_code == 200
    assert can.json()["status"] == "cancelled"


def test_api_stock_events_overview(client):
    c, _ = client
    st = c.get("/api/v1/dms/ops/stock")
    assert st.status_code == 200
    assert "rows" in st.json()
    ov = c.get("/api/v1/dms/ops/overview")
    assert ov.status_code == 200
    body = ov.json()
    assert "open_quotes" in body
    ev = c.get("/api/v1/dms/ops/events?limit=5")
    assert ev.status_code == 200


def _stock(c, sku="6L80-PUMP-01", location="CHI-N"):
    rows = c.get("/api/v1/dms/ops/stock").json()["rows"]
    for r in rows:
        if r.get("sku") == sku and r.get("location_code") == location:
            return r
    return None


def test_api_release_duplicate_idempotency_key(client):
    c, root = client
    c.post("/api/v1/dms/ops/receive", json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 3})
    res = c.post(
        "/api/v1/dms/ops/reserve",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 1},
    )
    assert res.status_code == 200, res.text
    rid = res.json()["reservation_id"]
    before = _stock(c)
    key = "api-rel-dup-1"
    r1 = c.post(f"/api/v1/dms/ops/reservations/{rid}/release?idempotency_key={key}")
    assert r1.status_code == 200, r1.text
    mid = _stock(c)
    r2 = c.post(f"/api/v1/dms/ops/reservations/{rid}/release?idempotency_key={key}")
    assert r2.status_code == 200, r2.text
    assert r2.json().get("idempotent") is True
    after = _stock(c)
    assert mid["reserved"] == after["reserved"] == before["reserved"] - 1
    # second release without key still conflicts (state protection preserved)
    bare = c.post(f"/api/v1/dms/ops/reservations/{rid}/release")
    assert bare.status_code == 409
    # no duplicate RELEASE events for the same gesture key
    svc = DmsService(root)
    n = svc.store.fetchone(
        "SELECT COUNT(*) AS c FROM inventory_events WHERE event_type = 'RELEASE' AND ref_id = ?",
        (str(rid),),
    )
    assert int(n["c"]) == 1
    svc.store.close()


def test_api_quote_reserve_cancel_convert_order_keys(client):
    c, root = client
    c.post("/api/v1/dms/ops/receive", json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 10})

    # --- quote reserve duplicate key ---
    q = c.post("/api/v1/dms/ops/quotes", json={"customer_label": "Key Shop"}).json()
    qid = q["id"]
    c.post(
        f"/api/v1/dms/ops/quotes/{qid}/lines",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 1, "unit_price_cents": 10000},
    )
    before = _stock(c)
    rkey = "api-qres-dup-1"
    r1 = c.post(f"/api/v1/dms/ops/quotes/{qid}/reserve?idempotency_key={rkey}")
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "reserved"
    mid = _stock(c)
    r2 = c.post(f"/api/v1/dms/ops/quotes/{qid}/reserve?idempotency_key={rkey}")
    assert r2.status_code == 200, r2.text
    assert r2.json().get("idempotent") is True
    assert r2.json()["status"] == "reserved"
    after = _stock(c)
    assert mid["reserved"] == after["reserved"] == before["reserved"] + 1

    # --- convert duplicate key ---
    ckey = "api-qconv-dup-1"
    o1 = c.post(f"/api/v1/dms/ops/quotes/{qid}/convert?idempotency_key={ckey}")
    assert o1.status_code == 200, o1.text
    oid = o1.json()["id"]
    assert o1.json()["status"] == "open"
    o2 = c.post(f"/api/v1/dms/ops/quotes/{qid}/convert?idempotency_key={ckey}")
    assert o2.status_code == 200, o2.text
    assert o2.json().get("idempotent") is True
    assert o2.json()["id"] == oid
    svc = DmsService(root)
    n_orders = svc.store.fetchone(
        "SELECT COUNT(*) AS c FROM orders WHERE quote_id = ?", (qid,)
    )
    assert int(n_orders["c"]) == 1
    svc.store.close()

    # --- order complete duplicate key ---
    stock_before = _stock(c)
    pkey = "api-ocomp-dup-1"
    d1 = c.post(f"/api/v1/dms/ops/orders/{oid}/complete?idempotency_key={pkey}")
    assert d1.status_code == 200, d1.text
    assert d1.json()["status"] == "completed"
    stock_mid = _stock(c)
    d2 = c.post(f"/api/v1/dms/ops/orders/{oid}/complete?idempotency_key={pkey}")
    assert d2.status_code == 200, d2.text
    assert d2.json().get("idempotent") is True
    stock_after = _stock(c)
    assert stock_mid["on_hand"] == stock_after["on_hand"] == stock_before["on_hand"] - 1
    svc = DmsService(root)
    n_sale = svc.store.fetchone(
        "SELECT COUNT(*) AS c FROM inventory_events WHERE event_type = 'SALE' AND ref_id = ?",
        (str(oid),),
    )
    assert int(n_sale["c"]) == 1
    svc.store.close()

    # --- quote cancel duplicate key (separate quote) ---
    q2 = c.post("/api/v1/dms/ops/quotes", json={"customer_label": "Cancel Key"}).json()
    q2id = q2["id"]
    c.post(
        f"/api/v1/dms/ops/quotes/{q2id}/lines",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 1},
    )
    c.post(f"/api/v1/dms/ops/quotes/{q2id}/reserve")
    can_key = "api-qcan-dup-1"
    before_c = _stock(c)
    c1 = c.post(f"/api/v1/dms/ops/quotes/{q2id}/cancel?idempotency_key={can_key}")
    assert c1.status_code == 200, c1.text
    assert c1.json()["status"] == "cancelled"
    mid_c = _stock(c)
    c2 = c.post(f"/api/v1/dms/ops/quotes/{q2id}/cancel?idempotency_key={can_key}")
    assert c2.status_code == 200, c2.text
    assert c2.json().get("idempotent") is True
    after_c = _stock(c)
    assert mid_c["reserved"] == after_c["reserved"] == before_c["reserved"] - 1

    # --- order cancel duplicate key ---
    q3 = c.post("/api/v1/dms/ops/quotes", json={"customer_label": "Order Cancel Key"}).json()
    q3id = q3["id"]
    c.post(
        f"/api/v1/dms/ops/quotes/{q3id}/lines",
        json={"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 1},
    )
    c.post(f"/api/v1/dms/ops/quotes/{q3id}/reserve")
    ord3 = c.post(f"/api/v1/dms/ops/quotes/{q3id}/convert").json()
    oid3 = ord3["id"]
    ocan_key = "api-ocan-dup-1"
    before_o = _stock(c)
    x1 = c.post(f"/api/v1/dms/ops/orders/{oid3}/cancel?idempotency_key={ocan_key}")
    assert x1.status_code == 200, x1.text
    assert x1.json()["status"] == "cancelled"
    mid_o = _stock(c)
    x2 = c.post(f"/api/v1/dms/ops/orders/{oid3}/cancel?idempotency_key={ocan_key}")
    assert x2.status_code == 200, x2.text
    assert x2.json().get("idempotent") is True
    after_o = _stock(c)
    assert mid_o["reserved"] == after_o["reserved"] == before_o["reserved"] - 1
    assert mid_o["on_hand"] == after_o["on_hand"] == before_o["on_hand"]
