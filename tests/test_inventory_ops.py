"""Inventory ops + quotes/orders — event ledger, reservations, concurrency."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from parrts.dms.ops import InventoryOps, OpsConflictError, OpsValidationError
from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed


def _ops() -> tuple[InventoryOps, TemporaryDirectory]:
    tmp = TemporaryDirectory()
    dms = DmsService(Path(tmp.name))
    dms.ensure_schema()
    load_demo_seed(dms)
    return InventoryOps(dms), tmp


def test_receive_increases_on_hand():
    ops, tmp = _ops()
    before = ops.stock_view(sku="6L80-PUMP-01")
    base = sum(r["on_hand"] for r in before if r["location_code"] == "CHI-N")
    r = ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5, reference="PO-1")
    assert r["on_hand"] == base + 5
    assert r["available"] == r["on_hand"] - r["reserved"]
    tmp.cleanup()


def test_adjust_up_and_down_and_reason_required():
    ops, tmp = _ops()
    with pytest.raises(OpsValidationError):
        ops.adjust(sku="6L80-PUMP-01", location="CHI-N", delta=1, reason="")
    up = ops.adjust(
        sku="6L80-PUMP-01", location="CHI-N", delta=2, reason="found_inventory"
    )
    down = ops.adjust(
        sku="6L80-PUMP-01",
        location="CHI-N",
        delta=-1,
        reason="physical_count_correction",
    )
    assert down["on_hand"] == up["on_hand"] - 1
    tmp.cleanup()


def test_adjust_cannot_go_negative():
    ops, tmp = _ops()
    with pytest.raises(OpsValidationError):
        ops.adjust(
            sku="6L80-PUMP-01",
            location="CHI-N",
            delta=-9999,
            reason="data_correction",
        )
    tmp.cleanup()


def test_transfer_atomic_and_conserves():
    ops, tmp = _ops()
    rows = ops.stock_view(sku="6L80-PUMP-01")
    total_before = sum(r["on_hand"] for r in rows)
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=4)
    ops.transfer(
        sku="6L80-PUMP-01",
        from_location="CHI-N",
        to_location="OHARE",
        qty=2,
    )
    rows2 = ops.stock_view(sku="6L80-PUMP-01")
    total_after = sum(r["on_hand"] for r in rows2)
    assert total_after == total_before + 4
    tmp.cleanup()


def test_transfer_cannot_exceed_available():
    ops, tmp = _ops()
    with pytest.raises(OpsConflictError):
        ops.transfer(
            sku="6L80-PUMP-01",
            from_location="CHI-N",
            to_location="OHARE",
            qty=9999,
        )
    tmp.cleanup()


def test_reservation_decreases_available_not_on_hand():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    r = ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=2)
    assert r["on_hand"] == before["on_hand"]
    assert r["reserved"] == before["reserved"] + 2
    assert r["available"] == before["available"] - 2
    ops.release_reservation(reservation_id=r["reservation_id"])
    after = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    assert after["available"] == before["available"]
    tmp.cleanup()


def test_reservation_above_available_rejected():
    ops, tmp = _ops()
    with pytest.raises(OpsConflictError):
        ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=9999)
    tmp.cleanup()


def test_release_twice_fails():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=2)
    r = ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=1)
    ops.release_reservation(reservation_id=r["reservation_id"])
    with pytest.raises(OpsConflictError):
        ops.release_reservation(reservation_id=r["reservation_id"])
    tmp.cleanup()


def test_concurrent_reservation_cannot_oversell():
    tmp = TemporaryDirectory()
    root = Path(tmp.name)
    dms = DmsService(root)
    dms.ensure_schema()
    load_demo_seed(dms)
    ops = InventoryOps(dms)
    view = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    ops.adjust(
        sku="6L80-PUMP-01",
        location="CHI-N",
        final_qty=1 + view["reserved"],
        reason="data_correction",
    )
    dms.store.close()

    results: list[str] = []
    lock = threading.Lock()

    def attempt(i: int) -> None:
        local = InventoryOps(DmsService(root))
        try:
            local.reserve(
                sku="6L80-PUMP-01",
                location="CHI-N",
                qty=1,
                idempotency_key=f"conc-{i}",
            )
            with lock:
                results.append("ok")
        except OpsConflictError:
            with lock:
                results.append("conflict")
        except Exception as e:
            with lock:
                results.append(f"err:{type(e).__name__}")
        finally:
            local.store.close()

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(attempt, range(8)))
    assert results.count("ok") == 1, results
    assert results.count("conflict") >= 1, results
    final_ops = InventoryOps(DmsService(root))
    final = [
        r
        for r in final_ops.stock_view(sku="6L80-PUMP-01")
        if r["location_code"] == "CHI-N"
    ][0]
    assert final["available"] >= 0
    assert final["reserved"] <= final["on_hand"]
    final_ops.store.close()
    tmp.cleanup()


def test_quote_lifecycle_to_sale():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5)
    before = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    q = ops.create_quote(customer_label="Lake Front Transmissions")
    q = ops.add_quote_line(
        quote_id=q["id"],
        sku="6L80-PUMP-01",
        location="CHI-N",
        qty=1,
        unit_price_cents=24500,
    )
    assert q["total_cents"] == 24500
    q = ops.reserve_quote(quote_id=q["id"])
    assert q["status"] == "reserved"
    mid = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    assert mid["reserved"] == before["reserved"] + 1
    assert mid["on_hand"] == before["on_hand"]
    order = ops.convert_quote_to_order(quote_id=q["id"])
    assert order["status"] == "open"
    order = ops.complete_order(order_id=order["id"])
    assert order["status"] == "completed"
    after = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    assert after["on_hand"] == before["on_hand"] - 1
    assert after["reserved"] == before["reserved"]
    # double complete fails
    with pytest.raises(OpsConflictError):
        ops.complete_order(order_id=order["id"])
    tmp.cleanup()


def test_cancel_quote_releases_reservation():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    q = ops.create_quote(customer_label="Test")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1)
    ops.reserve_quote(quote_id=q["id"])
    ops.cancel_quote(quote_id=q["id"])
    after = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    assert after["reserved"] == before["reserved"]
    assert after["on_hand"] == before["on_hand"]
    tmp.cleanup()


def test_cancel_open_order_releases():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    q = ops.create_quote(customer_label="Test")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1)
    ops.reserve_quote(quote_id=q["id"])
    order = ops.convert_quote_to_order(quote_id=q["id"])
    ops.cancel_order(order_id=order["id"])
    after = [r for r in ops.stock_view(sku="6L80-PUMP-01") if r["location_code"] == "CHI-N"][0]
    assert after["on_hand"] == before["on_hand"]
    assert after["reserved"] == before["reserved"]
    tmp.cleanup()
