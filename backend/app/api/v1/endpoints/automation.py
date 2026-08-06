"""
Automation results API — runs ledger, HIL alerts, email→order bridge, rulesets.

Offline SQLite via ``parrts.automation.AutomationService``. Soft-loaded.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import require_user_if_production
from app.models.user import User

router = APIRouter()


def resolve_monorepo_root() -> Path:
    for env_key in ("PARRTS_ROOT", "DMS_ROOT", "EMAIL_ROOT"):
        raw = (os.environ.get(env_key) or "").strip()
        if raw:
            p = Path(raw).expanduser().resolve()
            if p.is_dir():
                return p

    here = Path(__file__).resolve()
    candidates = list(here.parents) + [Path.cwd().resolve(), *Path.cwd().resolve().parents]
    for p in candidates:
        if (p / ".parrts").exists() or (p / "src" / "parrts").is_dir():
            return p
    return here.parents[5]


def get_automation_service():
    try:
        from parrts.automation import AutomationService
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"parrts.automation unavailable: {exc}",
        ) from exc
    return AutomationService(root=resolve_monorepo_root())


class RulesetBody(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class EmailToOrderBody(BaseModel):
    confirm: bool = False


class ResolveAlertBody(BaseModel):
    pass


@router.get("/status")
async def automation_status(
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    return get_automation_service().status()


@router.get("/results")
async def automation_results(
    limit: int = Query(50, ge=1, le=500),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    return get_automation_service().results_summary(limit_runs=limit)


@router.get("/runs")
async def list_runs(
    kind: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    requires_human: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    runs = get_automation_service().list_runs(
        kind=kind,
        status=status_filter,
        requires_human=requires_human,
        limit=limit,
    )
    return {"ok": True, "count": len(runs), "runs": runs}


@router.get("/alerts")
async def list_alerts(
    unresolved_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    alerts = get_automation_service().list_alerts(
        unresolved_only=unresolved_only,
        limit=limit,
    )
    return {"ok": True, "count": len(alerts), "alerts": alerts}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    try:
        return get_automation_service().resolve_alert(int(alert_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/rulesets")
async def get_rulesets(
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    return {"ok": True, "rulesets": get_automation_service().get_rulesets()}


@router.put("/rulesets")
async def put_rulesets(
    body: RulesetBody,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    rs = get_automation_service().update_rulesets(body.data or {})
    return {"ok": True, "rulesets": rs}


@router.post("/email/{email_id}/to-order")
async def email_to_order(
    email_id: int,
    body: EmailToOrderBody | None = None,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    confirm = bool(body.confirm) if body else False
    try:
        return get_automation_service().email_to_order(int(email_id), confirm=confirm)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        # BridgeError and stock errors → 400/409
        msg = str(exc)
        code = 409 if "stock" in msg.lower() or "Insufficient" in msg else 400
        raise HTTPException(status_code=code, detail=msg) from exc
