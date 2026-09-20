"""Deterministic transmission inquiry resolver (PARTS project).

Wired to canonical DMS via TransmissionRepository.
"""
from __future__ import annotations

import re

from parrts.dms.service import DmsService
from .models import TransmissionInquiryResult
from .repository import TransmissionRepository


def resolve_inquiry(query: str, dms: DmsService) -> TransmissionInquiryResult:
    """Resolve a transmission inquiry against the canonical DMS."""
    repo = TransmissionRepository(dms)
    q = query.lower()

    result = TransmissionInquiryResult(query=query)

    # Basic parsing
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        result.year = int(year_match.group(1))

    if "tahoe" in q:
        result.make = "Chevrolet"
        result.model = "Tahoe"
    elif "yukon" in q:
        result.make = "GMC"
        result.model = "Yukon"

    if "6l80" in q:
        result.transmission_family = "6L80"
    elif "6l90" in q:
        result.transmission_family = "6L90"

    if "pump" in q:
        result.part_type = "pump"
    elif "valve body" in q:
        result.part_type = "valve_body"

    if not result.transmission_family or not result.part_type:
        result.fitment_status = "insufficient"
        result.uncertainty.append("transmission family or part type not clearly identified")
        return result

    # Query canonical data
    candidates = repo.find_parts_by_family_and_type(
        result.transmission_family, result.part_type
    )

    if candidates:
        result.matched_skus = [c["sku"] for c in candidates]
        result.fitment_status = "compatible"

        first_sku = result.matched_skus[0]
        inv = repo.get_inventory(first_sku)
        available = [i for i in inv if i.get("qty", 0) > 0]
        result.inventory_available = len(available) > 0

        if available:
            result.notes = f"Found {len(available)} locations with stock"
        else:
            result.notes = "No available inventory in demo data"

        result.aliases_found = [
            f"{i['identifier_type']}:{i['identifier_value']}"
            for i in repo.get_identifiers(first_sku)
        ]

        inter = repo.get_interchanges(first_sku)
        result.interchange_candidates = [
            f"{i['target_sku']} ({i['relationship_type']}, {i['verification_status']})"
            for i in inter
        ]
    else:
        result.fitment_status = "no_match"
        result.uncertainty.append("No matching catalog parts found in demo data")

    return result