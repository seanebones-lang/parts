"""Celery OEM feed schedule — fail closed without OEM_FEED_URL."""

from __future__ import annotations

import os
from typing import Any


def run_scheduled_oem_sync(*, root: str | None = None) -> dict[str, Any]:
    """
    Sync OEM over HTTP when OEM_FEED_URL is set.

    Returns skipped=true when unconfigured (never invents catalog rows).
    """
    url = (os.environ.get("OEM_FEED_URL") or "").strip()
    if not url:
        return {
            "ok": True,
            "skipped": True,
            "reason": "OEM_FEED_URL not set — refusing synthetic live sync",
        }

    from pathlib import Path

    from parrts.dms.oem import HttpOemFeed
    from parrts.dms.service import DmsService

    token = (os.environ.get("OEM_FEED_TOKEN") or "").strip() or None
    monorepo = Path(root) if root else Path(os.environ.get("PARRTS_ROOT") or Path.cwd())
    svc = DmsService(root=monorepo)
    feed = HttpOemFeed(url, token=token)
    try:
        result = svc.sync_oem(feed, source=f"http:{url}")
        reindex = False
        if (os.environ.get("OEM_SYNC_REINDEX") or "").strip().lower() in {
            "1",
            "true",
            "yes",
        }:
            result["reindex"] = svc.reindex_rag()
            reindex = True
        return {"ok": True, "skipped": False, "reindex": reindex, **result}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "skipped": False, "error": str(exc)[:500]}


try:
    from app.celery import celery_app

    @celery_app.task(name="oem.scheduled_sync")
    def scheduled_oem_sync() -> dict[str, Any]:
        return run_scheduled_oem_sync()

except Exception:  # noqa: BLE001 — celery optional at import

    def scheduled_oem_sync() -> dict[str, Any]:  # type: ignore[misc]
        return run_scheduled_oem_sync()
