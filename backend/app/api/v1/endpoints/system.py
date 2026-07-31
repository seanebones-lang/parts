"""System integration status — key-gated production modules."""

from __future__ import annotations

import os

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/integrations")
async def integrations_status():
    """Report which external integrations are configured (no secrets returned)."""
    stripe = bool(
        (getattr(settings, "STRIPE_SECRET_KEY", None) or os.getenv("STRIPE_SECRET_KEY") or "").strip()
    )
    easypost = bool(
        (getattr(settings, "EASYPOST_API_KEY", None) or os.getenv("EASYPOST_API_KEY") or "").strip()
    )
    oem = bool((os.getenv("OEM_FEED_URL") or "").strip())
    return {
        "ok": True,
        "auth_mode": settings.AUTH_MODE,
        "environment": getattr(settings, "ENVIRONMENT", "development"),
        "stripe_configured": stripe,
        "easypost_configured": easypost,
        "oem_feed_configured": oem,
        "dms_mode": "embedded_sqlite",
        "notes": {
            "stripe": "Set STRIPE_SECRET_KEY to activate /api/v1/payments",
            "easypost": "Set EASYPOST_API_KEY to activate shipping labels",
            "oem": "Set OEM_FEED_URL (+ OEM_FEED_TOKEN) for live catalog sync",
        },
    }
