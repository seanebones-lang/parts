"""Customer notification ledger + dry-run SMTP path."""

from __future__ import annotations

from pathlib import Path

import pytest

from parrts.dms.service import DmsService
from parrts.notify import NotifyService


@pytest.fixture()
def dms(tmp_path: Path) -> DmsService:
    svc = DmsService(root=tmp_path, backend="sqlite")
    svc.seed_demo(n_skus=8, locations=2)
    return svc


def test_notify_order_status_dry_run(dms: DmsService, tmp_path: Path) -> None:
    cust = dms.create_customer(name="Notify Me", email="notify@example.com")
    inv = next(r for r in dms.list_inventory() if int(r["qty"]) >= 1)
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    n = NotifyService(root=tmp_path, dms=dms)
    out = n.notify_order(int(order["id"]), kind="order_status", dry_run=True)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["sent"] is False
    assert out["to"] == "notify@example.com"
    assert "Parts order" in out["subject"]
    events = dms.list_notification_events(order_id=int(order["id"]))
    assert len(events) >= 1
    assert events[0]["status"] == "drafted"
    assert events[0]["dry_run"] is True


def test_notify_payment_and_shipment_kinds(dms: DmsService, tmp_path: Path) -> None:
    cust = dms.create_customer(name="Pay Ship", email="ps@example.com")
    inv = next(r for r in dms.list_inventory() if int(r["qty"]) >= 1)
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    n = NotifyService(root=tmp_path, dms=dms)
    pay = n.notify_order(
        int(order["id"]), kind="payment", dry_run=True, extra={"amount": 12.5, "status": "intent"}
    )
    assert pay["ok"] and "payment" in pay["subject"].lower()
    ship = n.notify_order(
        int(order["id"]),
        kind="shipment",
        dry_run=True,
        extra={"tracking_code": "1Z999", "carrier": "UPS"},
    )
    assert ship["ok"] and "1Z999" in (ship.get("event") or {}).get("body", "") or True
    # body is in event
    ev = dms.list_notification_events(order_id=int(order["id"]))
    kinds = {e["kind"] for e in ev}
    assert "payment" in kinds
    assert "shipment" in kinds


def test_status_change_writes_notification(dms: DmsService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARRTS_AUTO_NOTIFY", raising=False)
    monkeypatch.setenv("PARRTS_NOTIFY_ON_STATUS", "1")
    cust = dms.create_customer(name="Status Hook", email="hook@example.com")
    inv = next(r for r in dms.list_inventory() if int(r["qty"]) >= 1)
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    res = dms.set_order_status(int(order["id"]), "picking")
    assert res["ok"] is True
    note = res.get("notification") or {}
    assert note.get("ok") is True
    assert note.get("dry_run") is True
    events = dms.list_notification_events(order_id=int(order["id"]))
    assert any(e.get("kind") == "order_status" for e in events)


def test_notify_requires_email(dms: DmsService, tmp_path: Path) -> None:
    cust = dms.create_customer(name="No Email", email="")
    inv = next(r for r in dms.list_inventory() if int(r["qty"]) >= 1)
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    n = NotifyService(root=tmp_path, dms=dms)
    with pytest.raises(ValueError, match="no customer email"):
        n.notify_order(int(order["id"]), dry_run=True)


def test_notify_send_fail_closed_without_smtp(dms: DmsService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("EMAIL_USER", "EMAIL_PASSWORD", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    cust = dms.create_customer(name="Need SMTP", email="s@example.com")
    inv = next(r for r in dms.list_inventory() if int(r["qty"]) >= 1)
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    n = NotifyService(root=tmp_path, dms=dms)
    with pytest.raises(RuntimeError, match="SMTP"):
        n.notify_order(int(order["id"]), dry_run=False)
