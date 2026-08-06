"""NotifyService — customer email notices for order/pay/ship (ledger + SMTP)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from parrts.notify.templates import render_order_status, render_payment, render_shipment


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


class NotifyService:
    """
    Customer notifications backed by DMS ``notification_events``.

    Default: dry-run draft (records ledger, no SMTP).
    Live send only when SMTP configured **and** (explicit confirm or PARRTS_AUTO_NOTIFY).
    Never invents delivery.
    """

    def __init__(self, root: Path | str, dms: Any | None = None) -> None:
        self.root = Path(root).resolve()
        if dms is None:
            from parrts.dms.service import DmsService

            dms = DmsService(root=self.root)
        self.dms = dms

    def smtp_status(self) -> dict[str, Any]:
        from parrts.email.mail_io import MailboxConfig

        cfg = MailboxConfig.from_env()
        return {
            "smtp_configured": cfg.smtp_configured(),
            "auto_notify": _env_bool("PARRTS_AUTO_NOTIFY", False),
            "from": cfg.from_address if cfg.smtp_configured() else None,
        }

    def notify_order(
        self,
        order_id: int,
        *,
        kind: str = "order_status",
        dry_run: bool | None = None,
        actor: str = "",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        order = self.dms.get_order(int(order_id))
        to_addr = (order.get("customer_email") or "").strip()
        if not to_addr or "@" not in to_addr:
            raise ValueError(f"order {order_id} has no customer email")

        extra = extra or {}
        k = (kind or "order_status").strip().lower()
        if k in {"order_status", "status", "invoice"}:
            subject, body = render_order_status(order)
            if k == "invoice":
                subject = f"Parts order #{order_id} — invoice"
        elif k in {"payment", "pay"}:
            subject, body = render_payment(
                order,
                amount=extra.get("amount"),
                status=str(extra.get("status") or order.get("payment_status") or "recorded"),
            )
        elif k in {"shipment", "ship", "shipping"}:
            subject, body = render_shipment(
                order,
                tracking_code=str(extra.get("tracking_code") or ""),
                carrier=str(extra.get("carrier") or ""),
                status=str(extra.get("status") or order.get("ship_status") or "labeled"),
            )
        else:
            subject, body = render_order_status(order)
            subject = f"Parts order #{order_id} — {k}"

        smtp = self.smtp_status()
        # dry_run default: True unless auto_notify + smtp
        if dry_run is None:
            dry_run = not (smtp["auto_notify"] and smtp["smtp_configured"])

        status = "drafted"
        message = "dry_run — not sent"
        configured = bool(smtp["smtp_configured"])

        if not dry_run:
            if not configured:
                raise RuntimeError(
                    "SMTP not configured — set EMAIL_USER + EMAIL_PASSWORD, or use dry_run=true"
                )
            from parrts.email.mail_io import send_smtp_message

            send_smtp_message(to_address=to_addr, subject=subject, body=body)
            status = "sent"
            message = "smtp_sent"

        event = self.dms.record_notification_event(
            order_id=int(order_id),
            kind=k,
            channel="email",
            to_address=to_addr,
            subject=subject,
            body=body,
            status=status,
            dry_run=bool(dry_run),
            configured=configured,
            message=message,
            actor=actor,
        )
        return {
            "ok": True,
            "dry_run": bool(dry_run),
            "sent": status == "sent",
            "to": to_addr,
            "subject": subject,
            "event": event.get("event") if isinstance(event, dict) else event,
            "smtp": smtp,
        }

    def list_events(self, *, order_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return self.dms.list_notification_events(order_id=order_id, limit=limit)
