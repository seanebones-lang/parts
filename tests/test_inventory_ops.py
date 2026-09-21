"""Inventory ops + quotes/orders — event ledger, reservations, concurrency, idempotency."""
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


def _chi(ops: InventoryOps, sku: str = "6L80-PUMP-01") -> dict:
    return [r for r in ops.stock_view(sku=sku) if r["location_code"] == "CHI-N"][0]


def test_receive_increases_on_hand():
    ops, tmp = _ops()
    before = _chi(ops)
    r = ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5, reference="PO-1")
    assert r["on_hand"] == before["on_hand"] + 5
    assert r["available"] == r["on_hand"] - r["reserved"]
    tmp.cleanup()


def test_adjust_up_and_down_and_reason_required():
    ops, tmp = _ops()
    with pytest.raises(OpsValidationError):
        ops.adjust(sku="6L80-PUMP-01", location="CHI-N", delta=1, reason="")
    up = ops.adjust(sku="6L80-PUMP-01", location="CHI-N", delta=2, reason="found_inventory")
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
        ops.adjust(sku="6L80-PUMP-01", location="CHI-N", delta=-9999, reason="data_correction")
    tmp.cleanup()


def test_adjust_cannot_reduce_below_reserved():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=2)
    ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=2)
    chi = _chi(ops)
    # force on-hand down to reserved - 1
    with pytest.raises(OpsValidationError):
        ops.adjust(
            sku="6L80-PUMP-01",
            location="CHI-N",
            final_qty=max(0, chi["reserved"] - 1),
            reason="physical_count",
        )
    tmp.cleanup()


def test_transfer_atomic_and_conserves():
    ops, tmp = _ops()
    rows = ops.stock_view(sku="6L80-PUMP-01")
    total_before = sum(r["on_hand"] for r in rows)
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=4)
    ops.transfer(sku="6L80-PUMP-01", from_location="CHI-N", to_location="OHARE", qty=2)
    rows2 = ops.stock_view(sku="6L80-PUMP-01")
    total_after = sum(r["on_hand"] for r in rows2)
    assert total_after == total_before + 4
    tmp.cleanup()


def test_transfer_cannot_exceed_available():
    ops, tmp = _ops()
    with pytest.raises(OpsConflictError):
        ops.transfer(sku="6L80-PUMP-01", from_location="CHI-N", to_location="OHARE", qty=9999)
    tmp.cleanup()


def test_reservation_decreases_available_not_on_hand():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = _chi(ops)
    r = ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=2)
    assert r["on_hand"] == before["on_hand"]
    assert r["reserved"] == before["reserved"] + 2
    assert r["available"] == before["available"] - 2
    ops.release_reservation(reservation_id=r["reservation_id"])
    after = _chi(ops)
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
    view = _chi(ops)
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
    final = _chi(final_ops)
    assert final["available"] >= 0
    assert final["reserved"] <= final["on_hand"]
    final_ops.store.close()
    tmp.cleanup()


def test_quote_lifecycle_to_sale():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5)
    before = _chi(ops)
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
    mid = _chi(ops)
    assert mid["reserved"] == before["reserved"] + 1
    assert mid["on_hand"] == before["on_hand"]
    order = ops.convert_quote_to_order(quote_id=q["id"])
    assert order["status"] == "open"
    order = ops.complete_order(order_id=order["id"])
    assert order["status"] == "completed"
    after = _chi(ops)
    assert after["on_hand"] == before["on_hand"] - 1
    assert after["reserved"] == before["reserved"]
    # double complete is idempotent (no second inventory hit)
    again = ops.complete_order(order_id=order["id"])
    assert again.get("idempotent") is True
    after2 = _chi(ops)
    assert after2["on_hand"] == after["on_hand"]
    tmp.cleanup()


def test_cancel_quote_releases_reservation():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = _chi(ops)
    q = ops.create_quote(customer_label="Test")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1)
    ops.reserve_quote(quote_id=q["id"])
    ops.cancel_quote(quote_id=q["id"])
    after = _chi(ops)
    assert after["reserved"] == before["reserved"]
    assert after["on_hand"] == before["on_hand"]
    tmp.cleanup()


def test_cancel_open_order_releases():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = _chi(ops)
    q = ops.create_quote(customer_label="Test")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1)
    ops.reserve_quote(quote_id=q["id"])
    order = ops.convert_quote_to_order(quote_id=q["id"])
    ops.cancel_order(order_id=order["id"])
    after = _chi(ops)
    assert after["on_hand"] == before["on_hand"]
    assert after["reserved"] == before["reserved"]
    tmp.cleanup()


# ----- idempotency -----


def test_receive_idempotency_key_once():
    ops, tmp = _ops()
    before = _chi(ops)
    key = "recv-once-1"
    r1 = ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5, idempotency_key=key)
    r2 = ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5, idempotency_key=key)
    assert r2.get("idempotent") is True
    after = _chi(ops)
    assert after["on_hand"] == before["on_hand"] + 5
    assert r1["event_id"] == r2["event_id"] or r2.get("idempotent")
    tmp.cleanup()


def test_adjust_idempotency_key_once():
    ops, tmp = _ops()
    before = _chi(ops)
    key = "adj-once-1"
    ops.adjust(sku="6L80-PUMP-01", location="CHI-N", delta=3, reason="found", idempotency_key=key)
    ops.adjust(sku="6L80-PUMP-01", location="CHI-N", delta=3, reason="found", idempotency_key=key)
    after = _chi(ops)
    assert after["on_hand"] == before["on_hand"] + 3
    tmp.cleanup()


def test_transfer_idempotency_key_once():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=4)
    before_rows = ops.stock_view(sku="6L80-PUMP-01")
    before_total = sum(r["on_hand"] for r in before_rows)
    chi_b = _chi(ops)["on_hand"]
    key = "xfer-once-1"
    ops.transfer(
        sku="6L80-PUMP-01",
        from_location="CHI-N",
        to_location="OHARE",
        qty=1,
        idempotency_key=key,
    )
    ops.transfer(
        sku="6L80-PUMP-01",
        from_location="CHI-N",
        to_location="OHARE",
        qty=1,
        idempotency_key=key,
    )
    after_rows = ops.stock_view(sku="6L80-PUMP-01")
    assert sum(r["on_hand"] for r in after_rows) == before_total
    assert _chi(ops)["on_hand"] == chi_b - 1
    tmp.cleanup()


def test_reserve_idempotency_key_once():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    before = _chi(ops)
    key = "res-once-1"
    r1 = ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=1, idempotency_key=key)
    r2 = ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=1, idempotency_key=key)
    assert r2.get("idempotent") is True
    after = _chi(ops)
    assert after["reserved"] == before["reserved"] + 1
    assert r1["reservation_id"] == r2["reservation_id"]
    tmp.cleanup()


def test_event_ledger_rows_and_before_after():
    ops, tmp = _ops()
    before = _chi(ops)
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=2, reference="PO-88")
    events = ops.list_events(sku="6L80-PUMP-01", limit=5)
    assert events
    recv = next(e for e in events if e["event_type"] == "RECEIVE")
    assert int(recv["on_hand_before"]) == before["on_hand"]
    assert int(recv["on_hand_after"]) == before["on_hand"] + 2
    assert recv.get("ref_id") == "PO-88" or "PO" in str(recv.get("notes") or "")
    tmp.cleanup()


def test_reserved_never_exceeds_on_hand_and_available_non_negative():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=1)
    chi = _chi(ops)
    ops.reserve(sku="6L80-PUMP-01", location="CHI-N", qty=chi["available"])
    after = _chi(ops)
    assert after["reserved"] <= after["on_hand"]
    assert after["available"] >= 0
    tmp.cleanup()


# ----- quote consistency -----


def test_cannot_edit_reserved_quote_line():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=3)
    q = ops.create_quote(customer_label="Edit block")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1)
    line_id = q["lines"][0]["id"]
    ops.reserve_quote(quote_id=q["id"])
    with pytest.raises(OpsConflictError):
        ops.update_quote_line(quote_id=q["id"], line_id=line_id, qty=2)
    with pytest.raises(OpsConflictError):
        ops.remove_quote_line(quote_id=q["id"], line_id=line_id)
    tmp.cleanup()


def test_multi_line_quote_reserve_and_partial_fail_atomic():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=5)
    # second SKU may already exist in seed
    before_pump = _chi(ops)
    q = ops.create_quote(customer_label="Multi")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1, unit_price_cents=1000)
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-VB-01", location="CHI-N", qty=1, unit_price_cents=2000)
    assert len(q["lines"]) == 2
    # force second line impossible by oversizing
    q = ops.update_quote_line(quote_id=q["id"], line_id=q["lines"][1]["id"], qty=9999)
    with pytest.raises(OpsConflictError):
        ops.reserve_quote(quote_id=q["id"])
    after_pump = _chi(ops)
    assert after_pump["reserved"] == before_pump["reserved"]
    # no active reservations for quote
    res = ops.list_reservations(status="active")
    assert not any(int(r.get("quote_id") or 0) == int(q["id"]) for r in res)
    # fix qty and succeed multi-line
    q = ops.update_quote_line(quote_id=q["id"], line_id=q["lines"][1]["id"], qty=1)
    q = ops.reserve_quote(quote_id=q["id"])
    assert q["status"] == "reserved"
    order = ops.convert_quote_to_order(quote_id=q["id"])
    order = ops.complete_order(order_id=order["id"])
    assert order["status"] == "completed"
    tmp.cleanup()


def test_add_second_line_same_quote():
    ops, tmp = _ops()
    ops.receive(sku="6L80-PUMP-01", location="CHI-N", qty=2)
    q = ops.create_quote(customer_label="Same")
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=1)
    q = ops.add_quote_line(quote_id=q["id"], sku="6L80-VB-01", location="CHI-N", qty=1)
    assert len(q["lines"]) == 2
    assert q["status"] in ("open", "draft")
    tmp.cleanup()


def test_quote_line_price_cents():
    ops, tmp = _ops()
    q = ops.create_quote(customer_label="Price")
    q = ops.add_quote_line(
        quote_id=q["id"], sku="6L80-PUMP-01", location="CHI-N", qty=2, unit_price_cents=24500
    )
    assert q["lines"][0]["unit_price_cents"] == 24500
    assert abs(float(q["lines"][0]["unit_price"]) - 245.0) < 0.001
    assert abs(float(q["total"]) - 490.0) < 0.001
    q = ops.update_quote_line(quote_id=q["id"], line_id=q["lines"][0]["id"], unit_price_cents=10000)
    assert q["lines"][0]["unit_price_cents"] == 10000
    tmp.cleanup()
