"""Commerce key-gating unit tests (no network, no Stripe/EasyPost keys)."""

from __future__ import annotations

import pytest

from parrts.commerce import (
    create_payment_intent_for_order,
    get_shipping_rates,
    payment_status,
    shipping_status,
)


def test_payment_status_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    st = payment_status()
    assert st["ok"] is True
    assert st["configured"] is False
    assert st["live_ready"] is False


def test_shipping_status_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EASYPOST_API_KEY", raising=False)
    st = shipping_status()
    assert st["configured"] is False


def test_create_intent_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    out = create_payment_intent_for_order(amount=10.0, order_id=1)
    assert out["success"] is False
    assert out["configured"] is False
    assert "STRIPE" in out["error"]


def test_rates_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EASYPOST_API_KEY", raising=False)
    out = get_shipping_rates(
        from_address={"street1": "1 A", "city": "X", "state": "IL", "zip": "60601"},
        to_address={"street1": "2 B", "city": "Y", "state": "IL", "zip": "60602"},
    )
    assert out["success"] is False
    assert out["configured"] is False
