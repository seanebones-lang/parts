"""Application-level transmission inquiry service (PARTS).

Provides a stable, read-only entry point for consumers.
Does not expose repository, resolver internals, or DMS details.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from parrts.dms.service import DmsService
from .models import TransmissionInquiryResult
from .resolver import resolve_inquiry
from .repository import TransmissionRepository

import logging
import os

logger = logging.getLogger(__name__)


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
    # Formal unit-of-work decision (RESOLVED | NEEDS_HUMAN)
    outcome: str | None = None
    confidence: float | None = None
    recommended_action: str | None = None
    ambiguity_reason: str | None = None
    intent: str | None = None
    candidate_match_quality: str | None = None
    evidence_sufficiency: str | None = None
    decision_source: str | None = None
    request_id: str | None = None
    decision: dict | None = None


def answer_transmission_inquiry(query: str, dms: DmsService) -> TransmissionInquiryAnswer:
    """Main public entry point for transmission inquiries."""
    low_level = resolve_inquiry(query, dms)
    repo = TransmissionRepository(dms)

    if not low_level.matched_skus:
        status: Status = "no_match" if low_level.fitment_status == "no_match" else "insufficient"
        answer = TransmissionInquiryAnswer(
            query=query,
            status=status,
            uncertainty=low_level.uncertainty,
            human_readable=_build_no_match_summary(query, low_level)
        )
        _finalize_unit_of_work(answer, root=dms.root)
        _observe_jev_shadow(query, answer, root=dms.root)
        return answer

    # Ambiguity: multiple canonical candidates
    if len(low_level.matched_skus) > 1:
        answer = TransmissionInquiryAnswer(
            query=query,
            status="ambiguous",
            uncertainty=["multiple canonical parts match the inquiry"],
            human_readable="Multiple parts match. Please provide more detail.",
        )
        _finalize_unit_of_work(answer, root=dms.root)
        _observe_jev_shadow(query, answer, root=dms.root)
        return answer

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

    answer = TransmissionInquiryAnswer(
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

    _finalize_unit_of_work(answer, root=dms.root)
    _observe_jev_shadow(query, answer, root=dms.root)
    return answer


def _finalize_unit_of_work(
    answer: TransmissionInquiryAnswer,
    *,
    root: Path | str | None = None,
) -> None:
    """Attach bounded RESOLVED/NEEDS_HUMAN decision and best-effort ledger log."""
    try:
        from parrts.transmission.decision import (
            build_unit_of_work,
            persist_unit_of_work,
        )

        uow = build_unit_of_work(answer)
        d = uow.decision
        answer.outcome = d.outcome
        answer.confidence = d.confidence
        answer.recommended_action = d.recommended_action
        answer.ambiguity_reason = d.ambiguity_reason
        answer.intent = d.intent
        answer.candidate_match_quality = d.candidate_match_quality
        answer.evidence_sufficiency = d.evidence_sufficiency
        answer.decision_source = d.decision_source
        answer.request_id = uow.request_id
        answer.decision = uow.to_dict()
        persist_unit_of_work(root, uow)
    except Exception as exc:
        logger.warning("transmission_uow_finalize_failed: %s", exc)
        # Fail closed toward human review rather than silent resolve.
        if answer.outcome is None:
            answer.outcome = "NEEDS_HUMAN" if answer.status != "resolved" else "RESOLVED"
            answer.confidence = 0.5 if answer.status == "resolved" else 0.3
            answer.recommended_action = answer.recommended_action or (
                "Review evidence manually — decision layer unavailable."
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


def _observe_jev_shadow(
    query: str,
    answer: TransmissionInquiryAnswer,
    *,
    root: Path | str | None = None,
) -> None:
    """Run JEV in shadow mode after deterministic resolution.

    Never modifies the answer. Never raises into the caller.
    Safe for every deterministic status path.

    When ``root`` is provided, best-effort persists a diagnostic record to
    the separate automation ledger (``.parrts/automation.db``), never DMS.
    """
    try:
        if os.environ.get("JEV_SHADOW_ENABLED", "").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            return

        from parrts.email.jev_shadow import classify_shadow
        from parrts.transmission.jev_shadow_report import (
            persist_transmission_jev_shadow_observation,
        )

        # subject=truncated query, body=full query (benchmark-compatible shape)
        shadow = classify_shadow(subject=query[:200], body=query, sender_email="")

        base = {
            "query": query,
            "deterministic_status": answer.status,
            "deterministic_sku": answer.sku,
            "deterministic_inventory_available": answer.inventory_available,
        }

        if shadow is None or not isinstance(shadow, dict):
            logger.info(
                "jev_shadow_transmission",
                extra={**base, "jev_evaluation_status": "no_result"},
            )
            if root is not None:
                persist_transmission_jev_shadow_observation(
                    root,
                    query=query,
                    answer=answer,
                    jev_evaluation_status="no_result",
                    shadow=None,
                )
            return

        logger.info(
            "jev_shadow_transmission",
            extra={
                **base,
                "jev_evaluation_status": "result",
                "jev_label": shadow.get("label"),
                "jev_needs_human": shadow.get("needs_human"),
                "jev_choice_confidence": shadow.get("choice_confidence"),
                "jev_noul_probability": shadow.get("noul_probability"),
                "jev_model": shadow.get("model"),
            },
        )
        if root is not None:
            persist_transmission_jev_shadow_observation(
                root,
                query=query,
                answer=answer,
                jev_evaluation_status="result",
                shadow=shadow,
            )
    except Exception as exc:
        # Import failures, classifier exceptions, logging issues — all contained.
        logger.warning(
            "jev_shadow_transmission_failed",
            extra={
                "query": query,
                "deterministic_status": answer.status,
                "deterministic_sku": answer.sku,
                "error": str(exc),
            },
        )
        if root is not None:
            try:
                from parrts.transmission.jev_shadow_report import (
                    persist_transmission_jev_shadow_observation,
                )

                persist_transmission_jev_shadow_observation(
                    root,
                    query=query,
                    answer=answer,
                    jev_evaluation_status="error",
                    shadow=None,
                    error=str(exc),
                )
            except Exception:
                pass
