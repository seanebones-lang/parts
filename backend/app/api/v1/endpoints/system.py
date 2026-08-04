"""System integration status — key-gated production modules."""

from __future__ import annotations

import os

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/integrations")
async def integrations_status():
    """Report which external integrations are configured (no secrets returned)."""
    from parrts.commerce import easypost_api_key, payment_status, shipping_status, stripe_secret_key
    from parrts.dms.backend import resolve_backend

    stripe = bool(stripe_secret_key()) or bool(
        (getattr(settings, "STRIPE_SECRET_KEY", None) or os.getenv("STRIPE_SECRET_KEY") or "").strip()
    )
    easypost = bool(easypost_api_key()) or bool(
        (getattr(settings, "EASYPOST_API_KEY", None) or os.getenv("EASYPOST_API_KEY") or "").strip()
    )
    oem = bool((os.getenv("OEM_FEED_URL") or "").strip())
    try:
        dms = resolve_backend()
        dms_mode = dms.backend
    except Exception:  # noqa: BLE001
        dms_mode = os.getenv("DMS_BACKEND", "sqlite")

    pay = payment_status()
    ship = shipping_status()
    return {
        "ok": True,
        "auth_mode": settings.AUTH_MODE,
        "environment": getattr(settings, "ENVIRONMENT", "development"),
        "stripe_configured": stripe,
        "easypost_configured": easypost,
        "oem_feed_configured": oem,
        "dms_mode": dms_mode,
        "payments": pay,
        "shipping": ship,
        "notes": {
            "stripe": "Set STRIPE_SECRET_KEY — UI: /payments · API: /api/v1/payments/order-intent",
            "easypost": "Set EASYPOST_API_KEY — UI: /shipping · API: /api/v1/shipping/rates",
            "oem": "Set OEM_FEED_URL (+ OEM_FEED_TOKEN) for live catalog sync",
        },
    }
