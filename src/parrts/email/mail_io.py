"""IMAP ingest + SMTP send for email desk (stdlib; credential-gated)."""

from __future__ import annotations

import email
import email.policy
import imaplib
import os
import re
import smtplib
import ssl
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name, "1" if default else "0").lower()
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)) or default)
    except ValueError:
        return default


@dataclass
class MailboxConfig:
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    from_address: str = ""
    auto_send: bool = False  # only greens when True and SMTP configured

    @classmethod
    def from_env(cls) -> MailboxConfig:
        imap_user = _env("IMAP_USER") or _env("EMAIL_USER")
        imap_password = _env("IMAP_PASSWORD") or _env("EMAIL_PASSWORD")
        smtp_user = _env("EMAIL_USER") or _env("SMTP_USER") or imap_user
        smtp_password = _env("EMAIL_PASSWORD") or _env("SMTP_PASSWORD") or imap_password
        from_addr = _env("EMAIL_FROM") or smtp_user
        return cls(
            imap_host=_env("IMAP_HOST", "imap.gmail.com"),
            imap_port=_env_int("IMAP_PORT", 993),
            imap_user=imap_user,
            imap_password=imap_password,
            imap_folder=_env("IMAP_FOLDER", "INBOX") or "INBOX",
            smtp_host=_env("EMAIL_HOST") or _env("SMTP_HOST") or "smtp.gmail.com",
            smtp_port=_env_int("EMAIL_PORT", _env_int("SMTP_PORT", 587)),
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_use_tls=_env_bool("EMAIL_USE_TLS", True),
            from_address=from_addr,
            auto_send=_env_bool("EMAIL_AUTO_SEND", False),
        )

    def imap_configured(self) -> bool:
        return bool(self.imap_host and self.imap_user and self.imap_password)

    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.from_address)

    def status(self) -> dict[str, Any]:
        return {
            "imap_configured": self.imap_configured(),
            "smtp_configured": self.smtp_configured(),
            "auto_send": self.auto_send,
            "imap_host": self.imap_host if self.imap_configured() else None,
            "smtp_host": self.smtp_host if self.smtp_configured() else None,
            "from_address": self.from_address if self.smtp_configured() else None,
            "imap_folder": self.imap_folder,
        }


def _decode_payload(msg: Any) -> str:
    if msg.is_multipart():
        texts: list[str] = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    texts.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    texts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
        if texts:
            return "\n".join(texts).strip()
        # fallback html stripped lightly
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                try:
                    html = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    html = payload.decode("utf-8", errors="replace")
                return re.sub(r"<[^>]+>", " ", html)
        return ""
    try:
        return str(msg.get_content()).strip()
    except Exception:
        payload = msg.get_payload(decode=True) or b""
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace").strip()


def fetch_imap_messages(
    cfg: MailboxConfig | None = None,
    *,
    limit: int = 20,
    unseen_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch messages from IMAP. Raises RuntimeError if not configured.
    Returns list of dicts ready for EmailService.ingest.
    """
    cfg = cfg or MailboxConfig.from_env()
    if not cfg.imap_configured():
        raise RuntimeError(
            "IMAP not configured — set IMAP_USER + IMAP_PASSWORD (and optional IMAP_HOST)"
        )

    out: list[dict[str, Any]] = []
    ctx = ssl.create_default_context()
    with imaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port, ssl_context=ctx) as imap:
        imap.login(cfg.imap_user, cfg.imap_password)
        typ, _ = imap.select(cfg.imap_folder)
        if typ != "OK":
            raise RuntimeError(f"Cannot select folder {cfg.imap_folder}")
        criteria = "UNSEEN" if unseen_only else "ALL"
        typ, data = imap.search(None, criteria)
        if typ != "OK" or not data or not data[0]:
            return []
        ids = data[0].split()
        # newest last in many servers — take tail
        ids = ids[-int(limit) :]
        for num in reversed(ids):
            typ, msg_data = imap.fetch(num, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw, policy=email.policy.default)
            message_id = (msg.get("Message-ID") or "").strip() or f"imap-{num.decode()}"
            subject = str(msg.get("Subject") or "")
            from_hdr = str(msg.get("From") or "")
            # crude parse name <email>
            sender_email = from_hdr
            sender_name = ""
            m = re.search(r"<([^>]+)>", from_hdr)
            if m:
                sender_email = m.group(1).strip()
                sender_name = from_hdr[: m.start()].strip().strip('"')
            received_at = None
            try:
                date_hdr = msg.get("Date")
                if date_hdr:
                    received_at = parsedate_to_datetime(str(date_hdr)).isoformat()
            except Exception:
                received_at = None
            body = _decode_payload(msg)
            out.append(
                {
                    "message_id": message_id,
                    "subject": subject,
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "body_text": body,
                    "received_at": received_at,
                    "thread_id": (msg.get("In-Reply-To") or msg.get("References") or "")[:255]
                    or None,
                }
            )
    return out


def send_smtp_reply(
    *,
    to_address: str,
    subject: str,
    body: str,
    cfg: MailboxConfig | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> dict[str, Any]:
    """Send a plain-text reply via SMTP. Raises RuntimeError if not configured."""
    cfg = cfg or MailboxConfig.from_env()
    if not cfg.smtp_configured():
        raise RuntimeError(
            "SMTP not configured — set EMAIL_USER + EMAIL_PASSWORD (and optional EMAIL_HOST)"
        )
    if not to_address or "@" not in to_address:
        raise ValueError("invalid to_address")

    msg = EmailMessage()
    msg["From"] = cfg.from_address
    msg["To"] = to_address
    subj = subject or "(no subject)"
    if not re.match(r"(?i)^re:", subj.strip()):
        subj = f"Re: {subj}"
    msg["Subject"] = subj
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = references or in_reply_to
    msg.set_content(body or "")

    if cfg.smtp_use_tls and cfg.smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=context, timeout=30) as smtp:
            smtp.login(cfg.smtp_user, cfg.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if cfg.smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(cfg.smtp_user, cfg.smtp_password)
            smtp.send_message(msg)

    return {
        "ok": True,
        "to": to_address,
        "from": cfg.from_address,
        "subject": subj,
        "transport": "smtp",
    }


def mailbox_status() -> dict[str, Any]:
    cfg = MailboxConfig.from_env()
    st = cfg.status()
    st["ok"] = True
    st["config"] = asdict(cfg)
    # never leak password
    st["config"]["imap_password"] = "***" if cfg.imap_password else ""
    st["config"]["smtp_password"] = "***" if cfg.smtp_password else ""
    return st
