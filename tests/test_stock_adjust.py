"""Stock receive/adjust with immutable audit trail (Wave 27)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from parrts.dms.service import DmsService, InsufficientStockError
from parrts.rbac import can


def test_adjust_permissions() -> None:
    assert can("counter", "inventory.receive")
    assert not can("counter", "inventory.adjust")
    assert can("manager", "inventory.adjust")
    assert can("admin", "inventory.receive")


def test_receive_increases_qty_and_audits(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=7, n_skus=4, locations=2)
    row = dms.list_inventory()[0]
    sku = row["sku"]
    loc = row["location_code"]
    before = int(row["qty"])

    out = dms.adjust_stock(
        sku=sku,
        location=loc,
        delta=3,
        reason="receive",
        actor="counter1",
        role="counter",
        notes="PO-100",
    )
    assert out["ok"] is True
    adj = out["adjustment"]
    assert adj["qty_before"] == before
    assert adj["qty_after"] == before + 3
    assert adj["delta"] == 3
    assert adj["reason"] == "receive"

    inv = next(
        r
        for r in dms.list_inventory(location=loc)
        if r["sku"] == sku
    )
    assert int(inv["qty"]) == before + 3

    log = dms.list_stock_adjustments(sku=sku)
    assert len(log) >= 1
    assert log[0]["delta"] == 3
    assert log[0]["notes"] == "PO-100"

    st = dms.status()
    assert int(st.get("stock_adjustments") or 0) >= 1


def test_counter_cannot_negative_adjust(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=8, n_skus=3, locations=2)
    row = next(r for r in dms.list_inventory() if int(r["qty"]) >= 1)
    with pytest.raises(PermissionError):
        dms.adjust_stock(
            sku=row["sku"],
            location=row["location_code"],
            delta=-1,
            reason="damage",
            role="counter",
        )


def test_manager_write_off_and_no_negative_floor(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=9, n_skus=5, locations=2)
    row = next(r for r in dms.list_inventory() if int(r["qty"]) >= 2)
    sku, loc, before = row["sku"], row["location_code"], int(row["qty"])

    dms.adjust_stock(
        sku=sku,
        location=loc,
        delta=-1,
        reason="damage",
        role="manager",
        actor="mgr1",
    )
    mid = next(r for r in dms.list_inventory(location=loc) if r["sku"] == sku)
    assert int(mid["qty"]) == before - 1

    with pytest.raises(InsufficientStockError):
        dms.adjust_stock(
            sku=sku,
            location=loc,
            delta=-(before + 50),
            reason="write_off",
            role="manager",
        )


def test_receive_requires_positive(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=10, n_skus=2, locations=2)
    row = dms.list_inventory()[0]
    with pytest.raises(ValueError, match="positive"):
        dms.adjust_stock(
            sku=row["sku"],
            location=row["location_code"],
            delta=-2,
            reason="receive",
            role="counter",
        )
