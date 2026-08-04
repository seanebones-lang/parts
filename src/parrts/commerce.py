"""Key-gated commerce helpers — Stripe payments + EasyPost shipping.

Fail closed without credentials. Never invent charges or labels.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _env(*keys: str) -> str:
    for k in keys:
        v = (os.environ.get(k) or "").strip()
        if v:
            return v
    return ""


def stripe_secret_key() -> str:
    return _env("STRIPE_SECRET_KEY", "STRIPE_API_KEY")


def stripe_publishable_key() -> str:
    return _env("STRIPE_PUBLISHABLE_KEY")


def stripe_webhook_secret() -> str:
    return _env("STRIPE_WEBHOOK_SECRET")


def easypost_api_key() -> str:
    return _env("EASYPOST_API_KEY")


def payment_status() -> dict[str, Any]:
    secret = bool(stripe_secret_key())
    return {
        "ok": True,
        "provider": "stripe",
        "configured": secret,
        "publishable_key_set": bool(stripe_publishable_key()),
        "webhook_secret_set": bool(stripe_webhook_secret()),
        "live_ready": secret,
        "message": (
            "Stripe ready — create intents via /api/v1/payments/order-intent"
            if secret
            else "Set STRIPE_SECRET_KEY to activate payments (no fake charges)"
        ),
        "endpoints": {
            "config": "/api/v1/payments/config",
            "order_intent": "POST /api/v1/payments/order-intent",
            "create_intent": "POST /api/v1/payments/create-intent",
            "webhook": "POST /api/v1/payments/webhook",
        },
    }


def shipping_status() -> dict[str, Any]:
    key = bool(easypost_api_key())
    return {
        "ok": True,
        "provider": "easypost",
        "configured": key,
        "live_ready": key,
        "message": (
            "EasyPost ready — rates/labels via /api/v1/shipping/*"
            if key
            else "Set EASYPOST_API_KEY to activate shipping (no fake labels)"
        ),
        "endpoints": {
            "config": "/api/v1/shipping/config",
            "rates": "POST /api/v1/shipping/rates",
            "label": "POST /api/v1/shipping/label",
        },
    }


def create_payment_intent_for_order(
    *,
    amount: float,
    currency: str = "usd",
    order_id: str | int | None = None,
    customer_email: str | None = None,
    description: str | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a Stripe PaymentIntent when STRIPE_SECRET_KEY is set."""
    key = stripe_secret_key()
    if not key:
        return {
            "success": False,
            "configured": False,
            "error": "STRIPE_SECRET_KEY not configured — refusing to create payment",
        }
    if amount is None or float(amount) <= 0:
        return {"success": False, "configured": True, "error": "amount must be > 0"}

    try:
        import stripe
    except ImportError:
        return {
            "success": False,
            "configured": True,
            "error": "stripe package not installed (pip install stripe)",
        }

    stripe.api_key = key
    cents = int(round(float(amount) * 100))
    meta: dict[str, str] = dict(metadata or {})
    if order_id is not None:
        meta.setdefault("order_id", str(order_id))
    meta.setdefault("source", "parrts_commerce")

    try:
        kwargs: dict[str, Any] = {
            "amount": cents,
            "currency": (currency or "usd").lower(),
            "automatic_payment_methods": {"enabled": True},
            "description": description
            or (f"Parts order {order_id}" if order_id else "Parts payment"),
            "metadata": meta,
        }
        if customer_email:
            kwargs["receipt_email"] = customer_email
        intent = stripe.PaymentIntent.create(**kwargs)
        return {
            "success": True,
            "configured": True,
            "payment_intent": {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": float(amount),
                "currency": (currency or "usd").lower(),
                "status": intent.status,
            },
            "publishable_key_set": bool(stripe_publishable_key()),
        }
    except Exception as exc:  # noqa: BLE001 — surface provider errors
        return {"success": False, "configured": True, "error": f"Stripe error: {exc}"}


def _easypost_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    key = easypost_api_key()
    if not key:
        return {
            "success": False,
            "configured": False,
            "error": "EASYPOST_API_KEY not configured — refusing to call carrier APIs",
        }
    url = f"https://api.easypost.com/v2{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header("Content-Type", "application/json")
    # Basic auth: key as username
    import base64

    token = base64.b64encode(f"{key}:".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return {"success": True, "configured": True, "data": payload}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:800]
        return {
            "success": False,
            "configured": True,
            "error": f"EasyPost HTTP {exc.code}: {err_body}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "configured": True, "error": str(exc)}


def get_shipping_rates(
    *,
    from_address: dict[str, str],
    to_address: dict[str, str],
    parcel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rate shop via EasyPost shipment create (no buy)."""
    parcel = parcel or {"weight": 16.0}  # oz default
    body = {
        "shipment": {
            "from_address": from_address,
            "to_address": to_address,
            "parcel": parcel,
        }
    }
    result = _easypost_request("POST", "/shipments", body)
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    rates_raw = data.get("rates") or []
    rates = [
        {
            "id": r.get("id"),
            "carrier": r.get("carrier"),
            "service": r.get("service"),
            "rate": float(r.get("rate") or 0),
            "currency": r.get("currency") or "USD",
            "delivery_days": r.get("delivery_days"),
        }
        for r in rates_raw
    ]
    rates.sort(key=lambda x: x["rate"])
    return {
        "success": True,
        "configured": True,
        "shipment_id": data.get("id"),
        "rates": rates,
        "total_options": len(rates),
    }


def buy_shipping_label(
    *,
    shipment_id: str,
    rate_id: str,
) -> dict[str, Any]:
    """Purchase a label for an existing EasyPost shipment + rate."""
    if not shipment_id or not rate_id:
        return {"success": False, "error": "shipment_id and rate_id required"}
    result = _easypost_request(
        "POST",
        f"/shipments/{shipment_id}/buy",
        {"rate": {"id": rate_id}},
    )
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    postage = data.get("postage_label") or {}
    tracking = data.get("tracker") or {}
    return {
        "success": True,
        "configured": True,
        "shipment_id": data.get("id") or shipment_id,
        "tracking_code": data.get("tracking_code") or tracking.get("tracking_code"),
        "label_url": postage.get("label_url"),
        "carrier": (data.get("selected_rate") or {}).get("carrier"),
        "service": (data.get("selected_rate") or {}).get("service"),
        "rate": (data.get("selected_rate") or {}).get("rate"),
    }
