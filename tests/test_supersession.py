"""Wave 29 — supersession chains, payment ledger, compliance export."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from parrts.dms.service import DmsService
from parrts.rbac import can


def test_supersession_permissions() -> None:
    assert can("manager", "catalog.supersession")
    assert not can("counter", "catalog.supersession")
    assert can("manager", "compliance.export")
    assert not can("counter", "compliance.export")
    assert can("counter", "payments.read")


def test_supersession_chain_and_cycle(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=7, n_skus=5, locations=2)
    skus = [r["sku"] for r in dms.list_catalog()]
    assert len(skus) >= 3
    a, b, c = skus[0], skus[1], skus[2]

    # seed may already map a→b; replace cleanly
    dms.delete_supersession(a)
    r = dms.set_supersession(old_sku=a, new_sku=b, notes="a->b", actor="t")
    assert r["ok"] is True
    dms.set_supersession(old_sku=b, new_sku=c, notes="b->c", actor="t")

    res = dms.resolve_supersession(a)
    assert res["ok"] is True
    assert res["superseded"] is True
    assert res["current_sku"] == c
    assert res["chain"] == [a, b, c]

    with pytest.raises(ValueError, match="cycle"):
        dms.set_supersession(old_sku=c, new_sku=a)

    with pytest.raises(ValueError, match="differ"):
        dms.set_supersession(old_sku=a, new_sku=a)


def test_payment_event_and_order_stamp(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=8, n_skus=4, locations=2)
    inv = dms.list_inventory()
    row = next(r for r in inv if int(r["qty"]) >= 1)
    cust = dms.create_customer(name="Pay Co", email="p@test.local")
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": row["sku"], "qty": 1, "location_id": row["location_id"]}],
    )
    oid = int(order["id"])
    full = dms.get_order(oid)
    total = float(full.get("total") or 0) or 1.0
    ev = dms.record_payment_event(
        order_id=oid,
        amount=total,
        status="requires_payment_method",
        external_id="pi_test_1",
        configured=True,
        actor="test",
    )
    assert ev["ok"] is True
    assert ev["event"]["external_id"] == "pi_test_1"
    o2 = dms.get_order(oid)
    assert o2["payment_status"] == "requires_payment_method"
    assert o2["last_payment_id"] == "pi_test_1"
    events = dms.list_payment_events(order_id=oid)
    assert len(events) >= 1


def test_compliance_export_and_analytics_extras(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=9, n_skus=6, locations=2)
    inv = dms.list_inventory()
    row = next(r for r in inv if int(r["qty"]) >= 1)
    cust = dms.create_customer(name="Audit Co", email="a@test.local")
    dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": row["sku"], "qty": 1, "location_id": row["location_id"]}],
    )
    dms.record_payment_event(
        order_id=1,
        amount=10.0,
        status="created",
        configured=False,
        message="no stripe",
    )
    exp = dms.compliance_export(days=90)
    assert exp["ok"] is True
    assert exp["counts"]["orders"] >= 1
    assert "payment_events" in exp
    a = dms.analytics_summary()
    assert "dead_stock" in a
    assert isinstance(a["dead_stock"], list)
    assert "fill_rate" in a
    assert a["fill_rate"]["ordered_units"] >= 1
    assert a["supersessions"]["mapping_count"] >= 0
    assert a["payments"]["event_count"] >= 1
