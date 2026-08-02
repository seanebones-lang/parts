"""
Email processing tasks — wired to parrts.email.EmailService.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.celery import celery_app


def _root() -> Path:
    raw = (os.environ.get("PARRTS_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "src" / "parrts").is_dir() or (p / ".parrts").exists():
            return p
    return Path.cwd()


def _svc():
    from parrts.email import EmailService

    return EmailService(root=_root())


@celery_app.task(bind=True)
def process_new_emails(self):
    """Fetch IMAP (if configured) + process pending desk queue."""
    try:
        start = time.time()
        svc = _svc()
        fetched = {"fetched": 0, "ingested": 0}
        try:
            fetched = svc.fetch_imap(limit=int(os.environ.get("MAX_EMAILS_PER_BATCH") or 10))
        except RuntimeError:
            # IMAP not configured — process local queue only
            pass
        pending = svc.process(limit=int(os.environ.get("MAX_EMAILS_PER_BATCH") or 50))
        return {
            "status": "success",
            "imap": {"fetched": fetched.get("fetched"), "ingested": fetched.get("ingested")},
            "processed": pending.get("processed"),
            "desk_status": svc.status(),
            "processing_time": time.time() - start,
            "timestamp": time.time(),
        }
    except Exception as e:
        print(f"Error processing emails: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def process_single_email(self, email_data: dict):
    """Ingest one payload through the specialist desk."""
    try:
        start = time.time()
        svc = _svc()
        row = svc.ingest(
            subject=str(email_data.get("subject") or ""),
            body_text=str(email_data.get("body") or email_data.get("body_text") or ""),
            sender_email=str(
                email_data.get("sender_email") or email_data.get("from") or "unknown@local"
            ),
            sender_name=str(email_data.get("sender_name") or ""),
            message_id=email_data.get("message_id") or email_data.get("id"),
            process=True,
        )
        tl = row.get("traffic_light") or {}
        return {
            "email_id": row.get("id"),
            "classification": row.get("email_type"),
            "confidence": row.get("classification_confidence"),
            "department": row.get("department"),
            "priority": row.get("priority"),
            "traffic_light": tl.get("color") if isinstance(tl, dict) else tl,
            "requires_human": row.get("requires_human"),
            "specialist": row.get("specialist"),
            "processing_time": time.time() - start,
        }
    except Exception as e:
        print(f"Error processing single email: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
