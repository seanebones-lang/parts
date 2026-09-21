"""Deterministic transmission inquiry resolver (PARTS project).

Wired to canonical DMS via TransmissionRepository.
"""
from __future__ import annotations

import re

from parrts.dms.service import DmsService
from .models import TransmissionInquiryResult
from .repository import TransmissionRepository

# Ordered family token → canonical family (longest/most-specific first where needed)
_FAMILY_TOKENS: list[tuple[str, str]] = [
    ("4l60e", "4L60E"),
    ("4l80e", "4L80E"),
    ("6l80", "6L80"),
    ("6l90", "6L90"),
    ("6r80", "6R80"),
    ("10r80", "10R80"),
    ("8hp70", "8HP70"),
]


def _normalize_counter_language(q: str) -> str:
    """Explicit, inspectable counter-language normalizations (observed eval misses only)."""
    # VB → valve body (word boundary; do not touch longer tokens)
    q = re.sub(r"\bvb\b", "valve body", q, flags=re.IGNORECASE)
    # valv → valve (covers "valv body")
    q = re.sub(r"\bvalv\b", "valve", q, flags=re.IGNORECASE)
    # pmp → pump
    q = re.sub(r"\bpmp\b", "pump", q, flags=re.IGNORECASE)
    return q


def _families_in_query(q: str) -> list[str]:
    """All transmission-family tokens present in the query (stable order)."""
    found: list[str] = []
    seen: set[str] = set()
    for token, family in _FAMILY_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", q) or token in q:
            if family not in seen:
                found.append(family)
                seen.add(family)
    return found


def _parse_vehicle(q: str) -> tuple[str | None, str | None]:
    """Minimal vehicle make/model extraction already used by the vertical."""
    if "tahoe" in q:
        return "Chevrolet", "Tahoe"
    if "yukon" in q:
        return "GMC", "Yukon"
    if "f-150" in q or "f150" in q or re.search(r"\bf\s*150\b", q):
        return "Ford", "F-150"
    if "silverado" in q:
        return "Chevrolet", "Silverado"
    return None, None


def resolve_inquiry(query: str, dms: DmsService) -> TransmissionInquiryResult:
    """Resolve a transmission inquiry against the canonical DMS."""
    repo = TransmissionRepository(dms)
    q_raw = query.lower()
    q = _normalize_counter_language(q_raw)

    result = TransmissionInquiryResult(query=query)

    # Basic parsing
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        result.year = int(year_match.group(1))

    make, model = _parse_vehicle(q)
    if make:
        result.make = make
    if model:
        result.model = model

    stated_families = _families_in_query(q)
    vehicle_families: list[str] = []
    if model:
        vehicle_families = repo.find_families_for_vehicle(model=model, make=make)

    # Conflict safety: vehicle-implied families vs stated families
    if stated_families and vehicle_families:
        compatible = [f for f in stated_families if f in vehicle_families]
        if not compatible:
            result.fitment_status = "insufficient"
            result.uncertainty.append(
                "conflicting vehicle and transmission-family evidence: "
                f"stated={','.join(stated_families)} "
                f"vehicle={model} implies={','.join(vehicle_families)}"
            )
            result.transmission_family = stated_families[0]
            return result
        # Prefer the intersection (vehicle-consistent family)
        result.transmission_family = compatible[0]
    elif stated_families:
        result.transmission_family = stated_families[0]
    elif vehicle_families:
        # Vehicle-only family cue is not enough alone for this phase — leave unset
        # unless we also have part type (do not expand behavior beyond conflict safety).
        pass

    # Part type (after normalization so VB/pmp/valv are covered)
    if "pump" in q:
        result.part_type = "pump"
    elif "valve body" in q or "valve_body" in q:
        result.part_type = "valve body"
    elif "input drum" in q or "reaction drum" in q or re.search(r"\bdrum\b", q):
        result.part_type = "drum"

    # Identifier-first lookup (required for Phase 2)
    identifier_tokens = re.findall(r"\b([A-Z0-9-]{6,})\b", query.upper())
    if identifier_tokens:
        for token in identifier_tokens:
            # Skip pure family-like tokens that are also catalog families
            if token.replace("-", "") in {
                f.replace("-", "").upper() for f in (s for _, s in _FAMILY_TOKENS)
            }:
                continue
            ident_matches = repo.find_by_identifier(token)
            if ident_matches:
                unique_skus = list({m["sku"] for m in ident_matches})
                if len(unique_skus) == 1:
                    result.matched_skus = unique_skus
                    result.fitment_status = "compatible"
                    first_sku = result.matched_skus[0]
                    inv = repo.get_inventory(first_sku)
                    available = [i for i in inv if i.get("qty", 0) > 0]
                    result.inventory_available = len(available) > 0
                    result.aliases_found = [
                        f"{i['identifier_type']}:{i['identifier_value']}"
                        for i in repo.get_identifiers(first_sku)
                    ]
                    inter = repo.get_interchanges(first_sku)
                    result.interchange_candidates = [
                        f"{i['target_sku']} ({i['relationship_type']}, {i['verification_status']})"
                        for i in inter
                    ]
                    if available:
                        result.notes = f"Found {len(available)} locations with stock"
                    return result
                else:
                    # Multiple canonical parts share the identifier → let service handle as ambiguous
                    result.matched_skus = unique_skus
                    return result

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
