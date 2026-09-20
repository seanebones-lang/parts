"""Application-level transmission inquiry service (PARTS).

Provides a stable, read-only entry point for consumers.
Does not expose repository, resolver internals, or DMS details.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from parrts.dms.service import DmsService
from .models import TransmissionInquiryResult
from .resolver import resolve_inquiry
from .repository import TransmissionRepository


Status = Literal["resolved", "ambiguous", "no_match", "insufficient"]


@dataclass
class TransmissionInquiryAnswer:
    """Stable application result for a transmission inquiry."""
    query: str
    status: Status
    sku: str | None = None
    name: str | None = None
    transmission_family: str | None = None
    part_type: str | None = None
    fitment_status: str | None = None
    inventory: list[dict] = field(default_factory=list)
    aggregate_available: int = 0
    inventory_available: bool = False
    identifiers: list[dict] = field(default_factory=list)
    interchanges: list[dict] = field(default_factory=list)
    verification_status: str | None = None
    uncertainty: list[str] = field(default_factory=list)
    human_readable: str = ""


def answer_transmission_inquiry(query: str, dms: DmsService) -> TransmissionInquiryAnswer:
    """Main public entry point for transmission inquiries."""
    low_level = resolve_inquiry(query, dms)
    repo = TransmissionRepository(dms)

    if not low_level.matched_skus:
        status: Status = "no_match" if low_level.fitment_status == "no_match" else "insufficient"
        return TransmissionInquiryAnswer(
            query=query,
            status=status,
            uncertainty=low_level.uncertainty,
            human_readable=_build_no_match_summary(query, low_level)
        )

    # Ambiguity: multiple canonical candidates
    if len(low_level.matched_skus) > 1:
        return TransmissionInquiryAnswer(
            query=query,
            status="ambiguous",
            uncertainty=["multiple canonical parts match the inquiry"],
            human_readable="Multiple parts match. Please provide more detail.",
        )

    # Single canonical match
    sku = low_level.matched_skus[0]

    # Fetch canonical details
    inv_rows = repo.get_inventory(sku)
    ident_rows = repo.get_identifiers(sku)
    inter_rows = repo.get_interchanges(sku)

    aggregate = sum(r.get("qty", 0) for r in inv_rows)
    available = aggregate > 0

    # Simple deterministic summary
    human = _build_human_readable(
        query=query,
        sku=sku,
        family=low_level.transmission_family,
        part_type=low_level.part_type,
        inv_rows=inv_rows,
        aggregate=aggregate,
        interchanges=inter_rows,
        verification=low_level.notes
    )

    return TransmissionInquiryAnswer(
        query=query,
        status="resolved",
        sku=sku,
        transmission_family=low_level.transmission_family,
        part_type=low_level.part_type,
        fitment_status=low_level.fitment_status,
        inventory=inv_rows,
        aggregate_available=aggregate,
        inventory_available=available,
        identifiers=ident_rows,
        interchanges=inter_rows,
        verification_status="unverified",  # demo data
        uncertainty=low_level.uncertainty,
        human_readable=human
    )


def _build_human_readable(
    query: str,
    sku: str,
    family: str | None,
    part_type: str | None,
    inv_rows: list[dict],
    aggregate: int,
    interchanges: list[dict],
    verification: str
) -> str:
    if not inv_rows:
        return f"No inventory records found for {sku}."

    first = inv_rows[0]
    loc = first.get("location", "unknown")
    bin_ = first.get("bin", "")
    cond = first.get("condition", "unknown")

    summary = f"{sku} matches the requested {family or ''} {part_type or ''}. "
    summary += f"{aggregate} unit(s) available at {loc}"
    if bin_:
        summary += f", bin {bin_}"
    summary += f" ({cond}). "

    if interchanges:
        summary += "Interchange candidates exist (unverified). "

    if "unverified" in verification.lower():
        summary += "Demo data — unverified."

    return summary.strip()


def _build_no_match_summary(query: str, low_level: TransmissionInquiryResult) -> str:
    if low_level.uncertainty:
        return f"Unable to resolve: {', '.join(low_level.uncertainty)}"
    return "No matching transmission part found."