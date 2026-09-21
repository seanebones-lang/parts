"""
Inbound email desk API — ``parrts.email.EmailService`` (SQLite + optional IMAP/SMTP).

No Postgres required. Soft-loaded via ``app.api.v1.api``.
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


def get_email_service():
    try:
        from parrts.email import EmailService
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"parrts.email unavailable: {exc}",
        ) from exc
    return EmailService(root=resolve_monorepo_root())


class IngestEmailBody(BaseModel):
    subject: str = ""
    body: str = Field("", description="Plain-text body")
    body_text: Optional[str] = None
    sender_email: str = Field(..., min_length=3)
    sender_name: str = ""
    recipient_email: str = "parts@dealership.local"
    message_id: Optional[str] = None
    process: bool = True


class ProcessBody(BaseModel):
    email_id: Optional[int] = None
    limit: int = Field(50, ge=1, le=500)


class SeedBody(BaseModel):
    clear: bool = False
    process: bool = True
    # demo vertical isolation: "transmission" | "default" (or omit)
    vertical: Optional[str] = None


class FetchImapBody(BaseModel):
    limit: int = Field(20, ge=1, le=200)
    process: bool = True
    unseen_only: bool = True


class SendBody(BaseModel):
    body: Optional[str] = None
    force: bool = False
    dry_run: bool = False


class OverrideBody(BaseModel):
    color: str = Field(..., description="green|yellow|red")
    requires_human: Optional[bool] = None
    notes: Optional[str] = None


class DraftBody(BaseModel):
    suggested_response: str


@router.get("/status")
async def email_status(
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    return get_email_service().status()


@router.get("/mailbox")
async def mailbox_info(
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    from parrts.email.mail_io import mailbox_status

    return mailbox_status()


@router.get("/")
async def list_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    traffic_light: Optional[str] = Query(None, description="green|yellow|red"),
    email_type: Optional[str] = None,
    requires_human: Optional[bool] = None,
    q: Optional[str] = Query(None, description="Full-text search"),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    svc = get_email_service()
    if q and q.strip():
        rows = svc.search(q.strip(), limit=limit)
    else:
        rows = svc.list(
            status=status_filter,
            traffic_light=traffic_light,
            email_type=email_type,
            requires_human=requires_human,
            limit=limit,
            offset=skip,
        )
    return {"ok": True, "count": len(rows), "emails": rows, "status": svc.status()}


@router.get("/search")
async def search_emails(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    svc = get_email_service()
    rows = svc.search(q, limit=limit)
    return {"ok": True, "count": len(rows), "emails": rows}


@router.get("/{email_id}")
async def get_email(
    email_id: int,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    row = get_email_service().get(email_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"email {email_id} not found")
    return {"ok": True, "email": row}


@router.post("/ingest")
async def ingest_email(
    body: IngestEmailBody,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    svc = get_email_service()
    text = body.body_text if body.body_text is not None else body.body
    row = svc.ingest(
        subject=body.subject,
        body_text=text,
        sender_email=body.sender_email,
        sender_name=body.sender_name,
        recipient_email=body.recipient_email,
        message_id=body.message_id,
        process=body.process,
    )
    return {"ok": True, "email": row}


@router.post("/process")
async def process_emails(
    body: Optional[ProcessBody] = None,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    svc = get_email_service()
    payload = body or ProcessBody()
    result = svc.process(email_id=payload.email_id, limit=payload.limit)
    return {"ok": True, **result, "status": svc.status()}


@router.post("/seed")
async def seed_emails(
    body: Optional[SeedBody] = None,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    payload = body or SeedBody()
    return get_email_service().seed_demo(
        clear=payload.clear,
        process=payload.process,
        vertical=payload.vertical,
    )


@router.post("/fetch-imap")
async def fetch_imap(
    body: Optional[FetchImapBody] = None,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Pull unseen mail when IMAP_* credentials are set."""
    _ = current_user
    svc = get_email_service()
    payload = body or FetchImapBody()
    try:
        return svc.fetch_imap(
            limit=payload.limit,
            process=payload.process,
            unseen_only=payload.unseen_only,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/{email_id}/send")
async def send_email(
    email_id: int,
    body: Optional[SendBody] = None,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Approve + SMTP send (or dry_run / mark-only without SMTP)."""
    _ = current_user
    svc = get_email_service()
    payload = body or SendBody()
    try:
        row = svc.approve_and_send(
            email_id,
            body=payload.body,
            force=payload.force,
            dry_run=payload.dry_run,
        )
        return {"ok": True, "email": row}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{email_id}/override")
async def override_email(
    email_id: int,
    body: OverrideBody,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    try:
        row = get_email_service().override(
            email_id,
            color=body.color,
            requires_human=body.requires_human,
            notes=body.notes,
        )
        return {"ok": True, "email": row}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{email_id}/draft")
async def patch_draft(
    email_id: int,
    body: DraftBody,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    try:
        row = get_email_service().update_draft(email_id, body.suggested_response)
        return {"ok": True, "email": row}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{email_id}/polish")
async def polish_email(
    email_id: int,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    _ = current_user
    try:
        row = get_email_service().polish(email_id)
        return {"ok": True, "email": row}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
