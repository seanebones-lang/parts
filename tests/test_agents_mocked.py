"""Mocked happy-path unit tests for inventory / payment / shipping agents.

No DB, LLM, Stripe, or network — services and log_action are mocked.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "backend"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


def _patch_llm():
    """Avoid real LLMService construction side effects during agent __init__."""
    return patch("app.agents.base_agent.LLMService", return_value=MagicMock())


# ---------------------------------------------------------------------------
# InventoryManagerAgent
# ---------------------------------------------------------------------------


def test_inventory_manager_check_inventory_happy_path():
    from app.agents.inventory_manager import InventoryManagerAgent

    db = _make_db()
    inventory_items = [
        {
            "part_id": 1,
            "sku": "BP-001",
            "quantity_available": 2,
            "reorder_point": 5,
            "needs_reorder": True,
        },
        {
            "part_id": 2,
            "sku": "OF-100",
            "quantity_available": 20,
            "reorder_point": 5,
            "needs_reorder": False,
        },
    ]

    with _patch_llm(), patch(
        "app.agents.inventory_manager.InventoryService"
    ) as InvSvc, patch(
        "app.agents.inventory_manager.NotificationService"
    ) as NotifSvc:
        inv = MagicMock()
        inv.get_location_inventory = AsyncMock(return_value=inventory_items)
        InvSvc.return_value = inv
        NotifSvc.return_value = MagicMock()

        agent = InventoryManagerAgent(db)
        agent.log_action = AsyncMock()

        result = asyncio.run(
            agent.process({"action": "check_inventory", "location_id": 1})
        )

    assert result.success is True
    assert result.confidence == 0.9
    assert "check_inventory" in (result.message or "")
    assert result.data is not None
    assert result.data["inventory_summary"]["total_items"] == 2
    assert result.data["inventory_summary"]["reorder_needed"] == 1
    assert result.data["inventory_summary"]["in_stock"] == 2
    assert any(a["type"] == "reorder_needed" for a in result.data["alerts"])
    inv.get_location_inventory.assert_awaited_once_with(1)
    agent.log_action.assert_awaited()
    assert agent.log_action.await_args.kwargs.get("success") is True


def test_inventory_manager_process_receiving_happy_path():
    from app.agents.inventory_manager import InventoryManagerAgent

    db = _make_db()

    with _patch_llm(), patch(
        "app.agents.inventory_manager.InventoryService"
    ) as InvSvc, patch(
        "app.agents.inventory_manager.NotificationService"
    ) as NotifSvc:
        inv = MagicMock()
        inv.receive_inventory = AsyncMock(
            return_value={"success": True, "new_quantity": 15}
        )
        notif = MagicMock()
        notif.send_receiving_notification = AsyncMock(return_value=True)
        InvSvc.return_value = inv
        NotifSvc.return_value = notif

        agent = InventoryManagerAgent(db)
        agent.log_action = AsyncMock()

        result = asyncio.run(
            agent.process(
                {
                    "action": "process_receiving",
                    "location_id": 1,
                    "received_items": [
                        {
                            "part_id": 10,
                            "quantity": 5,
                            "cost": 12.5,
                            "batch_number": "B-1",
                        }
                    ],
                }
            )
        )

    assert result.success is True
    assert result.data["receiving_summary"]["items_processed"] == 1
    assert result.data["receiving_summary"]["successful"] == 1
    inv.receive_inventory.assert_awaited_once()
    notif.send_receiving_notification.assert_awaited_once()


# ---------------------------------------------------------------------------
# PaymentAgent
# ---------------------------------------------------------------------------


def test_payment_agent_create_payment_link_happy_path():
    from app.agents.payment_agent import PaymentAgent

    db = _make_db()
    payment_payload = {
        "success": True,
        "payment_link_id": "plink_test_123",
        "url": "https://pay.example/test",
        "invoice_id": 42,
    }

    with _patch_llm(), patch(
        "app.agents.payment_agent.PaymentService"
    ) as PaySvc, patch(
        "app.agents.payment_agent.NotificationService"
    ) as NotifSvc:
        pay = MagicMock()
        pay.create_payment_link = AsyncMock(return_value=payment_payload)
        notif = MagicMock()
        notif.send_payment_notification = AsyncMock(return_value=True)
        PaySvc.return_value = pay
        NotifSvc.return_value = notif

        agent = PaymentAgent(db)
        agent.log_action = AsyncMock()

        result = asyncio.run(
            agent.process(
                {
                    "action": "create_payment",
                    "invoice_id": 42,
                    "amount": 199.99,
                    "payment_type": "link",
                    "customer_id": 7,
                    "success_url": "https://app.example/ok",
                    "cancel_url": "https://app.example/cancel",
                }
            )
        )

    assert result.success is True
    assert result.confidence == 0.95
    assert "create_payment" in (result.message or "")
    assert result.data["success"] is True
    assert result.data["url"] == "https://pay.example/test"
    pay.create_payment_link.assert_awaited_once()
    notif.send_payment_notification.assert_awaited_once_with(
        invoice_id=42, payment_data=payment_payload
    )
    agent.log_action.assert_awaited()


def test_payment_agent_check_payment_status_happy_path():
    from app.agents.payment_agent import PaymentAgent

    db = _make_db()
    status_payload = {
        "success": True,
        "status": "succeeded",
        "payment_intent_id": "pi_test_abc",
        "amount": 50.0,
    }

    with _patch_llm(), patch(
        "app.agents.payment_agent.PaymentService"
    ) as PaySvc, patch(
        "app.agents.payment_agent.NotificationService"
    ) as NotifSvc:
        pay = MagicMock()
        pay.get_payment_status = AsyncMock(return_value=status_payload)
        PaySvc.return_value = pay
        NotifSvc.return_value = MagicMock()

        agent = PaymentAgent(db)
        agent.log_action = AsyncMock()

        result = asyncio.run(
            agent.process(
                {
                    "action": "check_payment_status",
                    "payment_intent_id": "pi_test_abc",
                }
            )
        )

    assert result.success is True
    assert result.data["status"] == "succeeded"
    pay.get_payment_status.assert_awaited_once_with("pi_test_abc")


# ---------------------------------------------------------------------------
# ShippingCoordinatorAgent
# ---------------------------------------------------------------------------


def test_shipping_coordinator_create_shipment_happy_path():
    from app.agents.shipping_coordinator import ShippingCoordinatorAgent

    db = _make_db()
    rates = [
        {
            "service_type": "ground",
            "carrier": "ups",
            "cost": 12.5,
            "delivery_days": 5,
            "available": True,
            "package_info": {"weight": 2, "length": 6, "width": 6, "height": 6},
        },
        {
            "service_type": "overnight",
            "carrier": "fedex",
            "cost": 45.0,
            "delivery_days": 1,
            "available": True,
            "package_info": {"weight": 2, "length": 6, "width": 6, "height": 6},
        },
    ]
    shipment_payload = {
        "success": True,
        "shipment": {
            "id": 99,
            "tracking_number": "1Z999AA10123456784",
            "carrier": "ups",
            "service_type": "ground",
        },
    }
    label_payload = {
        "success": True,
        "label": {"url": "https://labels.example/99.pdf", "format": "pdf"},
    }

    with _patch_llm(), patch(
        "app.agents.shipping_coordinator.ShippingService"
    ) as ShipSvc, patch(
        "app.agents.shipping_coordinator.TrackingService"
    ) as TrackSvc, patch(
        "app.agents.shipping_coordinator.LabelService"
    ) as LabelSvc:
        ship = MagicMock()
        ship.get_shipping_rates = AsyncMock(
            return_value={"success": True, "rates": rates}
        )
        ship.create_shipment = AsyncMock(return_value=shipment_payload)
        label = MagicMock()
        label.generate_shipping_label = AsyncMock(return_value=label_payload)
        ShipSvc.return_value = ship
        TrackSvc.return_value = MagicMock()
        LabelSvc.return_value = label

        agent = ShippingCoordinatorAgent(db)
        agent.log_action = AsyncMock()
        agent._send_tracking_notification = AsyncMock()

        result = asyncio.run(
            agent.process(
                {
                    "action": "create_shipment",
                    "order_id": 500,
                    "customer_id": 7,
                    "shipping_address": {
                        "street": "123 Main",
                        "city": "Chicago",
                        "state": "IL",
                        "zip": "60601",
                    },
                    "origin_address": {
                        "street": "1 Warehouse",
                        "city": "Chicago",
                        "state": "IL",
                        "zip": "60608",
                    },
                    "items": [{"weight": 2, "quantity": 1}],
                }
            )
        )

    assert result.success is True
    assert result.confidence == 0.95
    assert "create_shipment" in (result.message or "")
    assert result.data["success"] is True
    assert result.data["shipment"]["tracking_number"] == "1Z999AA10123456784"
    assert result.data["label"]["url"].endswith(".pdf")
    ship.get_shipping_rates.assert_awaited_once()
    ship.create_shipment.assert_awaited_once()
    # ground selected for cost efficiency
    assert ship.create_shipment.await_args.kwargs["service_type"] == "ground"
    assert ship.create_shipment.await_args.kwargs["carrier"] == "ups"
    label.generate_shipping_label.assert_awaited_once()
    agent._send_tracking_notification.assert_awaited_once_with(
        customer_id=7, tracking_number="1Z999AA10123456784"
    )
    agent.log_action.assert_awaited()


def test_shipping_coordinator_get_shipping_rates_happy_path():
    from app.agents.shipping_coordinator import ShippingCoordinatorAgent

    db = _make_db()
    rates = [
        {
            "service_type": "ground",
            "carrier": "ups",
            "cost": 10.0,
            "delivery_days": 4,
            "available": True,
        },
        {
            "service_type": "expedited",
            "carrier": "fedex",
            "cost": 25.0,
            "delivery_days": 2,
            "available": True,
        },
    ]

    with _patch_llm(), patch(
        "app.agents.shipping_coordinator.ShippingService"
    ) as ShipSvc, patch(
        "app.agents.shipping_coordinator.TrackingService"
    ), patch(
        "app.agents.shipping_coordinator.LabelService"
    ):
        ship = MagicMock()
        ship.get_shipping_rates = AsyncMock(
            return_value={"success": True, "rates": rates}
        )
        ShipSvc.return_value = ship

        agent = ShippingCoordinatorAgent(db)
        agent.log_action = AsyncMock()

        result = asyncio.run(
            agent.process(
                {
                    "action": "get_shipping_rates",
                    "origin_address": {"zip": "60608"},
                    "destination_address": {"zip": "60601"},
                    "package_info": {"weight": 3, "length": 8, "width": 6, "height": 4},
                }
            )
        )

    assert result.success is True
    assert result.data["success"] is True
    assert len(result.data["rates"]) == 2
    assert "recommendations" in result.data
    assert any(r["type"] == "cost_effective" for r in result.data["recommendations"])
