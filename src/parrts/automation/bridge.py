"""Email → DMS draft-order bridge (HIL confirm by default)."""

from __future__ import annotations

from typing import Any


class BridgeError(ValueError):
    """User-facing bridge failure."""


def _extract_from_email_row(email: dict[str, Any]) -> dict[str, Any]:
    extracted = email.get("extracted") or email.get("extracted_info") or {}
    if isinstance(extracted, str):
        import json

        try:
            extracted = json.loads(extracted)
        except Exception:
            extracted = {}
    if not isinstance(extracted, dict):
        extracted = {}
    return extracted


def _candidate_lines(
    email: dict[str, Any],
    *,
    default_qty: int = 1,
    dms: Any,
) -> list[dict[str, Any]]:
    """Build order lines from SKU mentions and/or RAG hits + inventory lookup."""
    extracted = _extract_from_email_row(email)
    qty = int(extracted.get("quantity") or default_qty)
    if qty <= 0:
        qty = default_qty

    skus: list[str] = []
    for s in extracted.get("sku_mentions") or []:
        if s and str(s) not in skus:
            skus.append(str(s))

    hits = email.get("hits") or []
    if isinstance(hits, str):
        import json

        try:
            hits = json.loads(hits)
        except Exception:
            hits = []

    for h in hits or []:
        if not isinstance(h, dict):
            continue
        raw_part = h.get("part")
        part = raw_part if isinstance(raw_part, dict) else h
        if not isinstance(part, dict):
            continue
        sku = part.get("sku") or part.get("part_number")
        if sku and str(sku) not in skus:
            skus.append(str(sku))

    if not skus:
        raise BridgeError("No SKU candidates on email — cannot draft order")

    inv_rows = dms.list_inventory() if hasattr(dms, "list_inventory") else []
    # map sku -> best location with stock
    by_sku: dict[str, list[dict[str, Any]]] = {}
    for row in inv_rows or []:
        s = str(row.get("sku") or "")
        if not s:
            continue
        by_sku.setdefault(s, []).append(row)

    lines: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for sku in skus[:10]:
        candidates = by_sku.get(sku) or []
        # try case-insensitive
        if not candidates:
            for k, v in by_sku.items():
                if k.lower() == sku.lower():
                    candidates = v
                    sku = k
                    break
        if not candidates:
            unresolved.append(sku)
            continue
        # prefer highest qty
        candidates = sorted(candidates, key=lambda r: int(r.get("qty") or 0), reverse=True)
        best = candidates[0]
        lid = best.get("location_id")
        if lid is None:
            unresolved.append(sku)
            continue
        avail = int(best.get("qty") or 0)
        use_qty = min(qty, avail) if avail > 0 else qty
        if avail <= 0:
            unresolved.append(f"{sku}:no_stock")
            continue
        lines.append(
            {
                "sku": sku,
                "location_id": int(lid),
                "qty": use_qty,
                "unit_price": float(best.get("price") or 0),
            }
        )

    if not lines:
        raise BridgeError(
            f"No in-stock inventory for candidate SKUs: {', '.join(unresolved) or 'none'}"
        )
    return lines


def ensure_customer(dms: Any, email: dict[str, Any]) -> dict[str, Any]:
    sender = (email.get("sender_email") or "").strip()
    name = (email.get("sender_name") or "").strip() or sender.split("@")[0] or "Email Customer"
    if not sender:
        raise BridgeError("sender_email required to create/find customer")

    # find by email
    customers = dms.list_customers() if hasattr(dms, "list_customers") else []
    for c in customers or []:
        if str(c.get("email") or "").lower() == sender.lower():
            return c
    return dms.create_customer(name=name, email=sender, phone="", company="")


def draft_order_from_email(
    *,
    dms: Any,
    email: dict[str, Any],
    confirm: bool = False,
    default_qty: int = 1,
    notes_prefix: str = "email-automation",
) -> dict[str, Any]:
    """
    Build a draft order payload from an email row.

    When ``confirm=False`` (default HIL), returns preview only — no stock move.
    When ``confirm=True``, creates the DMS order (reserves stock).
    """
    lines = _candidate_lines(email, default_qty=default_qty, dms=dms)
    customer = ensure_customer(dms, email)
    eid = email.get("id")
    notes = f"{notes_prefix} email_id={eid} subject={(email.get('subject') or '')[:80]}"
    preview = {
        "ok": True,
        "confirmed": False,
        "email_id": eid,
        "customer": customer,
        "lines": lines,
        "notes": notes,
        "status": "draft_preview",
    }
    if not confirm:
        preview["message"] = "HIL required — re-call with confirm=true to create order"
        return preview

    order = dms.create_order(
        customer_id=int(customer["id"]),
        lines=lines,
        notes=notes,
    )
    return {
        "ok": True,
        "confirmed": True,
        "email_id": eid,
        "customer": customer,
        "order": order,
        "status": "order_created",
        "message": f"Order #{order.get('id')} created from email {eid}",
    }
