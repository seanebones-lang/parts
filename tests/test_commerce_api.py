"""Offline commerce API tests — config + fail-closed mutating routes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Skip collection noise if httpx/fastapi missing in bare core env
pytest.importorskip("httpx")
pytest.importorskip("fastapi")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    monkeypatch.delenv("EASYPOST_API_KEY", raising=False)
    monkeypatch.setenv("AUTH_MODE", "demo")
    monkeypatch.setenv("ENVIRONMENT", "development")

    from app.api.deps import require_user_if_production
    from app.api.v1.endpoints import payments, shipping

    app = FastAPI()
    app.include_router(payments.router, prefix="/api/v1/payments")
    app.include_router(shipping.router, prefix="/api/v1/shipping")

    async def _open():
        return None

    app.dependency_overrides[require_user_if_production] = _open
    return TestClient(app)


def test_payment_config(client: TestClient) -> None:
    r = client.get("/api/v1/payments/config")
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is False
    assert body["provider"] == "stripe"


def test_order_intent_503_without_key(client: TestClient) -> None:
    r = client.post(
        "/api/v1/payments/order-intent",
        json={"amount": 12.5, "order_id": 9},
    )
    assert r.status_code == 503
    assert "STRIPE" in str(r.json().get("detail", "")).upper()


def test_shipping_config(client: TestClient) -> None:
    r = client.get("/api/v1/shipping/config")
    assert r.status_code == 200
    assert r.json()["configured"] is False


def test_shipping_rates_503_without_key(client: TestClient) -> None:
    r = client.post(
        "/api/v1/shipping/rates",
        json={
            "from_address": {
                "street1": "100 Dealer Way",
                "city": "Chicago",
                "state": "IL",
                "zip": "60601",
            },
            "to_address": {
                "street1": "200 Main",
                "city": "Naperville",
                "state": "IL",
                "zip": "60540",
            },
            "parcel": {"weight": 16},
        },
    )
    assert r.status_code == 503
