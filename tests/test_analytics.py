"""DMS operator analytics from real tables (Wave 28)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from parrts.dms.service import DmsService
from parrts.rbac import can


def test_analytics_permission() -> None:
    assert can("counter", "analytics.read")
    assert can("manager", "analytics.read")


def test_analytics_summary_from_seed(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=11, n_skus=6, locations=2)
    st = dms.status()
    a = dms.analytics_summary()

    assert a["ok"] is True
    assert a["source"] == "dms"
    assert a["counts"]["catalog_parts"] == st["catalog_parts"]
    assert a["counts"]["inventory_units"] == st["inventory_units"]
    assert a["counts"]["orders"] == st["orders"]
    assert isinstance(a["orders_by_status"], dict)
    assert isinstance(a["top_inventory_skus"], list)
    assert len(a["top_inventory_skus"]) >= 1
    assert "order_book_value" in a["revenue"]
    assert a["revenue"]["currency"] == "USD"
    # values are finite numbers
    assert float(a["revenue"]["order_book_value"]) >= 0.0


def test_analytics_reflects_order_and_adjust(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=12, n_skus=5, locations=2)
    inv = dms.list_inventory()
    row = next(r for r in inv if int(r["qty"]) >= 2)
    cust = dms.create_customer(name="Analytics Shop", email="a@test.local")

    dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": row["sku"], "qty": 1, "location_id": row["location_id"]}],
    )
    dms.adjust_stock(
        sku=row["sku"],
        location=row["location_code"],
        delta=2,
        reason="receive",
        actor="test",
        role="counter",
    )

    a = dms.analytics_summary()
    assert a["counts"]["orders"] >= 1
    assert sum(a["orders_by_status"].values()) == a["counts"]["orders"]
    assert a["counts"]["stock_adjustments"] >= 1
    reasons = {r["reason"] for r in a["adjustments_by_reason"]}
    assert "receive" in reasons
    assert a["revenue"]["order_book_value"] >= 0.0
