"""Wave 30 — ship-from-order shipment ledger."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from parrts.dms.service import DmsService


def test_shipment_event_stamps_order(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=30, n_skus=4, locations=2)
    inv = dms.list_inventory()
    row = next(r for r in inv if int(r["qty"]) >= 1)
    cust = dms.create_customer(name="Ship Co", email="s@test.local")
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": row["sku"], "qty": 1, "location_id": row["location_id"]}],
    )
    oid = int(order["id"])
    ev = dms.record_shipment_event(
        order_id=oid,
        status="labeled",
        external_id="shp_test",
        tracking_code="1ZTEST",
        label_url="https://example.com/label.pdf",
        carrier="USPS",
        service="Priority",
        rate=8.5,
        configured=True,
        actor="test",
    )
    assert ev["ok"] is True
    assert ev["event"]["tracking_code"] == "1ZTEST"
    o2 = dms.get_order(oid)
    assert o2["ship_status"] == "labeled"
    assert o2["tracking_code"] == "1ZTEST"
    assert o2["last_shipment_id"] == "shp_test"
    events = dms.list_shipment_events(order_id=oid)
    assert len(events) >= 1
    a = dms.analytics_summary()
    assert a["shipments"]["event_count"] >= 1
    exp = dms.compliance_export(days=90)
    assert exp["counts"].get("shipment_events", 0) >= 1
