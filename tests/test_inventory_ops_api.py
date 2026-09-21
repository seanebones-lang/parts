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
