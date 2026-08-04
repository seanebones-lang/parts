"""Inter-store transfer stock conservation + manager approval threshold."""

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


def test_transfer_permissions() -> None:
    assert can("counter", "transfers.write")
    assert not can("counter", "transfers.approve")
    assert can("manager", "transfers.approve")


def test_small_transfer_completes_and_conserves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARRTS_TRANSFER_APPROVAL_QTY", "10")
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=1, n_skus=5, locations=3)
    inv = dms.list_inventory()
    # pick a row with qty >= 2
    row = next(r for r in inv if int(r["qty"]) >= 2)
    sku = row["sku"]
    from_code = row["location_code"]
    locs = [loc["code"] for loc in dms.list_locations() if loc["code"] != from_code]
    to_code = locs[0]
    before = dms.sku_total_qty(sku)

    out = dms.create_transfer(
        sku=sku,
        from_location=from_code,
        to_location=to_code,
        qty=1,
        role="counter",
        requested_by="counter1",
    )
    assert out["ok"] is True
    assert out["transfer"]["status"] == "completed"
    assert out["conserved"] is True
    assert dms.sku_total_qty(sku) == before


def test_large_transfer_needs_manager_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PARRTS_TRANSFER_APPROVAL_QTY", "3")
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=2, n_skus=8, locations=4)
    inv = dms.list_inventory()
    row = next(r for r in inv if int(r["qty"]) >= 5)
    sku = row["sku"]
    from_code = row["location_code"]
    to_code = next(
        loc["code"] for loc in dms.list_locations() if loc["code"] != from_code
    )
    before = dms.sku_total_qty(sku)

    pending = dms.create_transfer(
        sku=sku,
        from_location=from_code,
        to_location=to_code,
        qty=5,
        role="counter",
        requested_by="counter1",
    )
    assert pending["transfer"]["status"] == "pending_approval"
    # stock unchanged while pending
    assert dms.sku_total_qty(sku) == before

    with pytest.raises(PermissionError):
        dms.approve_transfer(pending["transfer"]["id"], role="counter")

    done = dms.approve_transfer(
        pending["transfer"]["id"], role="manager", approved_by="mgr1"
    )
    assert done["transfer"]["status"] == "completed"
    assert done["conserved"] is True
    assert dms.sku_total_qty(sku) == before


def test_cancel_pending_no_stock_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PARRTS_TRANSFER_APPROVAL_QTY", "2")
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=3, n_skus=6, locations=3)
    inv = dms.list_inventory()
    row = next(r for r in inv if int(r["qty"]) >= 3)
    sku = row["sku"]
    from_code = row["location_code"]
    to_code = next(c["code"] for c in dms.list_locations() if c["code"] != from_code)
    before = dms.sku_total_qty(sku)
    p = dms.create_transfer(
        sku=sku, from_location=from_code, to_location=to_code, qty=3, role="counter"
    )
    tid = p["transfer"]["id"]
    dms.cancel_transfer(tid, role="manager", cancelled_by="mgr")
    assert dms.sku_total_qty(sku) == before
    assert dms._get_transfer_row(tid)["status"] == "cancelled"


def test_insufficient_stock_on_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PARRTS_TRANSFER_APPROVAL_QTY", "100")
    dms = DmsService(root=tmp_path)
    dms.seed_demo(seed=4, n_skus=4, locations=2)
    inv = dms.list_inventory()
    row = inv[0]
    with pytest.raises(InsufficientStockError):
        dms.create_transfer(
            sku=row["sku"],
            from_location=row["location_code"],
            to_location=next(
                c["code"] for c in dms.list_locations() if c["code"] != row["location_code"]
            ),
            qty=int(row["qty"]) + 50,
            role="admin",
            force_complete=True,
        )
