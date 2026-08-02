"""Inbound email auto-answer desk — selling point of Parts."""

from __future__ import annotations

from parrts.email.classify import Classification, classify_email
from parrts.email.mail_io import MailboxConfig, mailbox_status
from parrts.email.pipeline import EmailPipeline
from parrts.email.policy import EmailTrafficLight, grade_email
from parrts.email.service import EmailService
from parrts.email.store import EmailStore

__all__ = [
    "Classification",
    "EmailPipeline",
    "EmailService",
    "EmailStore",
    "EmailTrafficLight",
    "MailboxConfig",
    "classify_email",
    "grade_email",
    "mailbox_status",
]
