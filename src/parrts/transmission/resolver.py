"""Deterministic transmission inquiry resolver (Demo 1).

This resolver extracts structured information from natural language
inquiries without using an LLM. It is intentionally conservative.
"""
from __future__ import annotations

import re
from typing import Any

from .models import TransmissionInquiryResult


def resolve_inquiry(query: str) -> TransmissionInquiryResult:
    """Resolve a transmission-related inquiry into structured data."""
    q = query.lower()

    result = TransmissionInquiryResult(query=query)

    # Extract year
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", q)
    if year_match:
        result.year = int(year_match.group(1))

    # Extract make/model (very basic)
    if "tahoe" in q:
        result.make = "Chevrolet"
        result.model = "Tahoe"
    elif "yukon" in q:
        result.make = "GMC"
        result.model = "Yukon"

    # Detect transmission family
    if "6l80" in q:
        result.transmission_family = "6L80"
    elif "6l90" in q:
        result.transmission_family = "6L90"

    # Detect part type
    if "pump" in q:
        result.part_type = "pump"
    elif "valve body" in q or "valvebody" in q:
        result.part_type = "valve_body"

    # Simple fitment status logic (demo only)
    if result.transmission_family and result.part_type:
        if result.year and 2007 <= result.year <= 2014:
            result.fitment_status = "compatible"
        else:
            result.fitment_status = "candidate"
    elif result.transmission_family or result.part_type:
        result.fitment_status = "insufficient"
    else:
        result.fitment_status = "no_match"

    # Placeholder for inventory check (would query inventory_levels in real impl)
    result.inventory_available = False
    result.uncertainty.append("inventory check not yet wired to DMS")

    if not result.transmission_family:
        result.uncertainty.append("transmission family not clearly stated")

    return result