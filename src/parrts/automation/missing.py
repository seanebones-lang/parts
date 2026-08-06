"""Detect missing fields on inbound email / automation payloads (HIL alerts)."""

from __future__ import annotations

from typing import Any


def _has_sku_or_parts(extracted: dict[str, Any], hits: list[Any] | None = None) -> bool:
    skus = extracted.get("sku_mentions") or []
    parts = extracted.get("parts_requested") or []
    if skus or parts:
        return True
    if hits:
        for h in hits:
            part = h.get("part") if isinstance(h, dict) else None
            if isinstance(part, dict) and (part.get("sku") or part.get("part_number")):
                return True
            if isinstance(h, dict) and (h.get("sku") or h.get("part_number")):
                return True
    return False


def missing_fields_for_email(
    *,
    email_type: str | None,
    extracted: dict[str, Any] | None,
    hits: list[Any] | None = None,
    sender_email: str | None = None,
    rules: dict[str, Any] | None = None,
) -> list[str]:
    """Return list of missing field codes for HIL / alerts."""
    extracted = extracted or {}
    rules = rules or {}
    e2o = rules.get("email_to_order") or {}
    mf = rules.get("missing_fields") or {}
    order_types = set(mf.get("order_types") or ["parts_order", "quote_request"])
    et = (email_type or "").lower()
    missing: list[str] = []

    if et and et not in order_types and et != "unknown":
        # still check sender for all
        if not (sender_email or "").strip():
            missing.append("sender_email")
        return missing

    required = list(e2o.get("required_fields") or ["sku_or_parts", "sender_email"])
    for field in required:
        if field == "sender_email":
            if not (sender_email or "").strip():
                missing.append("sender_email")
        elif field == "sku_or_parts":
            if not _has_sku_or_parts(extracted, hits):
                missing.append("sku_or_parts")
        elif field == "vehicle_info":
            if not extracted.get("vehicle_info"):
                missing.append("vehicle_info")
        elif field == "quantity":
            if extracted.get("quantity") is None:
                missing.append("quantity")
        elif field == "phone":
            if not extracted.get("phone"):
                missing.append("phone")
        else:
            if not extracted.get(field):
                missing.append(field)

    preferred = list(e2o.get("preferred_fields") or [])
    for field in preferred:
        if field in missing:
            continue
        if field == "vehicle_info" and not extracted.get("vehicle_info"):
            missing.append(f"preferred:{field}")
        elif field == "quantity" and extracted.get("quantity") is None:
            missing.append(f"preferred:{field}")
        elif field == "phone" and not extracted.get("phone"):
            missing.append(f"preferred:{field}")

    return missing


def hard_missing(missing: list[str]) -> list[str]:
    """Fields that block auto-order (ignore preferred:*)."""
    return [m for m in missing if not m.startswith("preferred:")]
