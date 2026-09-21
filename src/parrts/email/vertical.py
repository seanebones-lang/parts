"""Resolve active PARRTS vertical from backend environment (not browser-only vars)."""

from __future__ import annotations

import os

TRANSMISSION_ALIASES = frozenset(
    {
        "transmission",
        "jp",
        "jp_transmission",
        "tx",
        "jp-transmission",
    }
)


def resolve_parrts_vertical(explicit: str | None = None) -> str:
    """Return 'transmission' or 'generic'.

    Order: explicit arg → PARRTS_VERTICAL → EMAIL_VERTICAL → generic.
    Browser NEXT_PUBLIC_* is never read here.
    """
    candidates = [
        explicit,
        os.environ.get("PARRTS_VERTICAL"),
        os.environ.get("EMAIL_VERTICAL"),
    ]
    for raw in candidates:
        if raw is None:
            continue
        v = str(raw).strip().lower()
        if not v:
            continue
        if v in TRANSMISSION_ALIASES:
            return "transmission"
        if v in ("generic", "default", "parts", "auto", "off", "0"):
            return "generic"
        # unknown token → treat non-empty as generic unless clearly transmission
        return "generic"
    return "generic"


def is_transmission_vertical(explicit: str | None = None) -> bool:
    return resolve_parrts_vertical(explicit) == "transmission"
