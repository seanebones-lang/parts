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
    if "prius" in q:
        return "Toyota", "Prius"
    return None, None


# Ordered part-type detectors (word-boundary; inspectable; not a fuzzy NLP table)
_PART_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # optional plural: "pump" / "pumps" (substring "pump" matched pre-guard)
    ("pump", re.compile(r"\bpumps?\b", re.IGNORECASE)),
    ("valve body", re.compile(r"\bvalve\s+bod(?:y|ies)\b|\bvalve_body\b", re.IGNORECASE)),
    ("drum", re.compile(r"\b(?:input\s+|reaction\s+)?drums?\b", re.IGNORECASE)),
]


def _part_types_in_query(q: str) -> list[str]:
    """All hard-part types present in the query (stable order, de-duped)."""
    found: list[str] = []
    seen: set[str] = set()
    for name, pat in _PART_TYPE_PATTERNS:
        if pat.search(q) and name not in seen:
            found.append(name)
            seen.add(name)
    return found


def _part_type_mention_count(q: str, part_type: str) -> int:
    """How many times a part-type token appears (for symmetric comparisons)."""
    if part_type == "valve body":
        return len(
            re.findall(
                r"\bvalve\s+bod(?:y|ies)\b|\bvalve_body\b", q, flags=re.IGNORECASE
            )
        )
    if part_type == "drum":
        return len(
            re.findall(r"\b(?:input\s+|reaction\s+)?drums?\b", q, flags=re.IGNORECASE)
        )
    if part_type == "pump":
        return len(re.findall(r"\bpumps?\b", q, flags=re.IGNORECASE))
    return 0


def competing_signal_reason(q: str, stated_families: list[str]) -> str | None:
    """Detect competing requested meanings that make a single-SKU answer unsafe.

    Deterministic and inspectable. Multi-family alone is NOT enough (vehicle /
    fitment disambiguation may still pick one family safely). Targets:
    multi-part-type, multi-item, comparative/substitution, and which-one choice.
    """
    part_types = _part_types_in_query(q)
    families = list(stated_families)

    # 1) Multiple distinct part types → do not pick one
    if len(part_types) >= 2:
        return (
            "competing part-type signals: "
            f"{', '.join(part_types)} — cannot return a single SKU"
        )

    # 2) Explicit multi-item language with a part request
    #    e.g. "… both now" after naming more than one thing; covered above when
    #    two part types appear. Also catch "and … both" with multi-family noise.
    if re.search(r"\bboth\b", q) and len(part_types) >= 1 and len(families) >= 2:
        # "6L80 6L90 pump both" style multi-family multi-item without second type
        if re.search(r"\band\b", q) or re.search(r"\bwhich\b", q):
            return (
                "multi-item request with competing family signals — "
                "single-SKU unit of work cannot resolve"
            )

    # 3) Comparison / substitution / which-one across multiple families
    if len(families) >= 2:
        if re.search(r"\bwhich one\b", q):
            return (
                "multiple transmission families with an explicit which-one choice"
            )
        if re.search(r"\binstead of\b", q):
            return "substitution request across transmission families"
        if re.search(r"\bcan i use\b", q):
            return "substitution/compatibility ask across transmission families"
        if re.search(r"\bcross[\s-]*over\b", q):
            return "crossover request across transmission families"

        # Symmetric "same as" comparison: part type appears on both sides
        # ("is 6R80 pump same as 6L80 pump?"). Asymmetric identify forms
        # ("same as 6L90 pump but for 6L80?") keep a single part-type mention
        # and remain eligible for ordinary resolve.
        if re.search(r"\bsame as\b", q) and part_types:
            if _part_type_mention_count(q, part_types[0]) >= 2:
                return (
                    "comparative same-as between two family+part claims"
                )

        # Disjunctive family choice: "6L80 or 6L90 pump"
        if re.search(r"\bor\b", q) and part_types:
            # "pump or valve body" already handled by multi part-type.
            # Family A or Family B (+ optional shared part type):
            fam_alt = re.search(
                r"\b(?:4l60e|4l80e|6l80|6l90|6r80|10r80|8hp70)\b"
                r"\s+or\s+"
                r"\b(?:4l60e|4l80e|6l80|6l90|6r80|10r80|8hp70)\b",
                q,
                flags=re.IGNORECASE,
            )
            if fam_alt:
                return "disjunctive transmission-family choice"

    # 4) Explicit uncertainty with competing part-type language already covered;
    #    "not sure which" + multi family without vehicle disambiguation path:
    if (
        re.search(r"\bnot sure which\b", q)
        and len(part_types) >= 2
    ):
        return "explicit uncertainty with competing part-type signals"

    return None


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

    # Conflict / no-fitment safety: vehicle cue vs stated families
    # Uses canonical part_fitments only (find_families_for_vehicle).
    if stated_families and model:
        if not vehicle_families:
            # Vehicle recognized but no canonical fitment rows at all for it —
            # do not bluff a family+part RESOLVED (Eval v2 V2-84 class).
            result.fitment_status = "insufficient"
            reason = (
                "vehicle/transmission fitment could not be verified: "
                f"vehicle={model} has no canonical fitment rows for "
                f"stated family={','.join(stated_families)}"
            )
            if re.search(r"\bcvt\b", q):
                reason += "; query also names CVT which conflicts with the stated family"
            result.uncertainty.append(reason)
            result.transmission_family = stated_families[0]
            return result
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

    # Part types (collect all; single type still drives ordinary resolve)
    part_types = _part_types_in_query(q)
    if part_types:
        result.part_type = part_types[0]

    # Competing-signal safety: multi-part / comparative / multi-item requests
    # must not collapse into one high-confidence family+part SKU.
    # Runs before identifier and catalog match so a single SKU is never emitted.
    # Vehicle/family conflict already returned above; E09-style vehicle-consistent
    # multi-family without comparison language is intentionally not blocked here.
    competing = competing_signal_reason(q, stated_families)
    if competing:
        result.fitment_status = "insufficient"
        result.uncertainty.append(competing)
        result.matched_skus = []
        return result

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
