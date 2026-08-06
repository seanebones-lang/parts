"""Customer notification templates (white-label Parts desk)."""

from __future__ import annotations

from typing import Any


def render_order_status(order: dict[str, Any]) -> tuple[str, str]:
    oid = order.get("id")
    st = order.get("status") or "updated"
    name = order.get("customer_name") or "Customer"
    total = order.get("total")
    total_s = f"${float(total):.2f}" if isinstance(total, (int, float)) else "—"
    lines = order.get("lines") or []
    body_lines = [
        f"Hi {name},",
        "",
        f"Update on your parts order #{oid}: status is now **{st}**.",
        f"Order total: {total_s}",
        "",
        "Lines:",
    ]
    for ln in lines[:20]:
        body_lines.append(
            f"  - {ln.get('sku')} × {ln.get('qty')} @ ${float(ln.get('unit_price') or 0):.2f}"
        )
    if order.get("tracking_code"):
        body_lines += ["", f"Tracking: {order.get('tracking_code')}"]
    body_lines += [
        "",
        "Thank you,",
        "Parts Desk",
        "(Automated notice — reply to this email if you have questions.)",
    ]
    # plain text without markdown bold
    body = "\n".join(body_lines).replace("**", "")
    subject = f"Parts order #{oid} — {st}"
    return subject, body


def render_payment(order: dict[str, Any], *, amount: float | None = None, status: str = "recorded") -> tuple[str, str]:
    oid = order.get("id")
    name = order.get("customer_name") or "Customer"
    amt = amount if amount is not None else order.get("paid_amount") or order.get("total") or 0
    subject = f"Parts order #{oid} — payment {status}"
    body = (
        f"Hi {name},\n\n"
        f"Payment update for order #{oid}: {status}.\n"
        f"Amount: ${float(amt or 0):.2f}\n"
        f"Payment status on file: {order.get('payment_status') or status}\n\n"
        "Thank you,\nParts Desk\n"
    )
    return subject, body


def render_shipment(
    order: dict[str, Any],
    *,
    tracking_code: str = "",
    carrier: str = "",
    status: str = "labeled",
) -> tuple[str, str]:
    oid = order.get("id")
    name = order.get("customer_name") or "Customer"
    track = tracking_code or order.get("tracking_code") or ""
    subject = f"Parts order #{oid} — shipment {status}"
    body = (
        f"Hi {name},\n\n"
        f"Shipment update for order #{oid}: {status}.\n"
        f"Carrier: {carrier or '—'}\n"
        f"Tracking: {track or '—'}\n\n"
        "Thank you,\nParts Desk\n"
    )
    return subject, body
