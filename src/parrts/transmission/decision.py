"""Bounded decision layer for one transmission hard-parts request (unit of work).

PARRTS/RAG/DMS gather evidence. This module evaluates whether the request is
safe to RESOLVE or must NEEDS_HUMAN. It is not a general conversational model.

JEV (when enabled + available) is an optional bounded gate on top of the
deterministic evidence policy. Offline/tests always get a complete decision
from the deterministic policy alone.
"""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

Outcome = Literal["RESOLVED", "NEEDS_HUMAN"]
MatchQuality = Literal["exact", "strong", "weak", "none", "ambiguous"]
EvidenceSufficiency = Literal["sufficient", "partial", "insufficient"]
Intent = Literal[
    "parts_availability",
    "price_request",
    "compatibility_fitment",
    "order_status",
    "general_question",
    "unknown",
]
DecisionSource = Literal["deterministic_policy", "deterministic_policy+jev"]

KIND = "transmission_request_uow"
SCHEMA_VERSION = "transmission_request_uow.v1"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class TransmissionEvidence:
    """Evidence gathered for one request (not a second inventory source of truth)."""

    query: str
    deterministic_status: str
    sku: str | None = None
    name: str | None = None
    transmission_family: str | None = None
    part_type: str | None = None
    fitment_status: str | None = None
    inventory_available: bool = False
    aggregate_available: int = 0
    inventory: list[dict[str, Any]] = field(default_factory=list)
    identifiers: list[dict[str, Any]] = field(default_factory=list)
    interchanges: list[dict[str, Any]] = field(default_factory=list)
    verification_status: str | None = None
    uncertainty: list[str] = field(default_factory=list)
    matched_sku_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TransmissionDecision:
    """Bounded JEV/policy decision for one request."""

    outcome: Outcome
    confidence: float
    intent: Intent
    candidate_match_quality: MatchQuality
    evidence_sufficiency: EvidenceSufficiency
    ambiguity_reason: str | None
    recommended_action: str
    decision_source: DecisionSource
    jev_consulted: bool = False
    jev_needs_human: bool | None = None
    jev_label: str | None = None
    jev_choice_confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TransmissionUnitOfWork:
    """
    One formal unit of work: a single transmission hard-parts request.

    Reserved fields (human_override, final_accepted_*) support later analytics
    without requiring a full analytics system now.
    """

    request_id: str
    created_at: str
    query: str
    evidence: TransmissionEvidence
    decision: TransmissionDecision
    # Customer-facing answer snapshot (mirrors TransmissionInquiryAnswer fields)
    status: str
    sku: str | None
    human_readable: str
    # Future audit hooks
    human_override: bool | None = None
    final_accepted_outcome: Outcome | None = None
    final_accepted_sku: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "request_id": self.request_id,
            "created_at": self.created_at,
            "query": self.query,
            "evidence": self.evidence.to_dict(),
            "decision": self.decision.to_dict(),
            "status": self.status,
            "sku": self.sku,
            "human_readable": self.human_readable,
            # Immutable system snapshot (retained after human feedback)
            "system_outcome": self.decision.outcome,
            "system_confidence": self.decision.confidence,
            "system_sku": self.sku,
            "system_status": self.status,
            "system_result": self.human_readable,
            "human_override": self.human_override,
            "final_accepted_outcome": self.final_accepted_outcome,
            "final_accepted_sku": self.final_accepted_sku,
            "final_accepted_at": None,
            "final_accepted_note": None,
            "final_result_recorded": False,
            "outcome": self.decision.outcome,
            "confidence": self.decision.confidence,
            "recommended_action": self.decision.recommended_action,
            "ambiguity_reason": self.decision.ambiguity_reason,
            "intent": self.decision.intent,
            "candidate_match_quality": self.decision.candidate_match_quality,
            "evidence_sufficiency": self.decision.evidence_sufficiency,
            "decision_source": self.decision.decision_source,
        }


def _infer_intent(query: str) -> Intent:
    q = (query or "").lower()
    if any(t in q for t in ("price", "quote", "cost", "how much")):
        return "price_request"
    if any(t in q for t in ("fit", "compatible", "interchange", "cross")):
        return "compatibility_fitment"
    if any(t in q for t in ("order", "tracking", "shipment", "delivery")):
        return "order_status"
    if any(t in q for t in ("have", "stock", "available", "pump", "valve", "sku", "oem")):
        return "parts_availability"
    return "unknown"


def evaluate_evidence_policy(evidence: TransmissionEvidence) -> TransmissionDecision:
    """Deterministic bounded policy from gathered evidence (always available)."""
    intent = _infer_intent(evidence.query)
    status = (evidence.deterministic_status or "").lower()
    verification = (evidence.verification_status or "").lower()
    uncertainty = list(evidence.uncertainty or [])

    if status == "resolved" and evidence.sku:
        if verification == "disputed":
            return TransmissionDecision(
                outcome="NEEDS_HUMAN",
                confidence=0.55,
                intent=intent,
                candidate_match_quality="strong",
                evidence_sufficiency="partial",
                ambiguity_reason="catalog verification status is disputed",
                recommended_action=(
                    "Verify the disputed catalog record with a counterperson before quoting."
                ),
                decision_source="deterministic_policy",
            )
        quality: MatchQuality = "exact" if evidence.identifiers else "strong"
        conf = 0.9 if quality == "exact" else 0.82
        if not evidence.inventory_available:
            conf = min(conf, 0.78)
            action = (
                f"Part identified as {evidence.sku}. Out of stock — offer interchange "
                "or source; do not invent availability."
            )
        else:
            action = (
                f"Quote {evidence.sku} from available inventory "
                f"({evidence.aggregate_available} unit(s)). Confirm bin/condition at counter."
            )
        return TransmissionDecision(
            outcome="RESOLVED",
            confidence=conf,
            intent=intent,
            candidate_match_quality=quality,
            evidence_sufficiency="sufficient",
            ambiguity_reason=None,
            recommended_action=action,
            decision_source="deterministic_policy",
        )

    if status == "ambiguous":
        reason = (
            uncertainty[0]
            if uncertainty
            else "multiple canonical parts match the inquiry"
        )
        return TransmissionDecision(
            outcome="NEEDS_HUMAN",
            confidence=0.45,
            intent=intent,
            candidate_match_quality="ambiguous",
            evidence_sufficiency="partial",
            ambiguity_reason=reason,
            recommended_action=(
                "Ask for OEM number, casting number, or exact SKU before selecting a part."
            ),
            decision_source="deterministic_policy",
        )

    if status == "insufficient":
        reason = (
            uncertainty[0]
            if uncertainty
            else "not enough identifying information"
        )
        return TransmissionDecision(
            outcome="NEEDS_HUMAN",
            confidence=0.35,
            intent=intent,
            candidate_match_quality="none",
            evidence_sufficiency="insufficient",
            ambiguity_reason=reason,
            recommended_action=(
                "Request transmission family, part type, and OEM/casting identifier."
            ),
            decision_source="deterministic_policy",
        )

    # no_match or unknown
    reason = uncertainty[0] if uncertainty else "no matching transmission part found"
    return TransmissionDecision(
        outcome="NEEDS_HUMAN",
        confidence=0.4,
        intent=intent,
        candidate_match_quality="none",
        evidence_sufficiency="insufficient",
        ambiguity_reason=reason,
        recommended_action=(
            "Escalate to counter: no catalog match. Collect OEM/casting and vehicle details."
        ),
        decision_source="deterministic_policy",
    )


def _maybe_consult_jev(query: str, decision: TransmissionDecision) -> TransmissionDecision:
    """Optional JEV gate. Never raises. Never invents a match JEV did not support."""
    enabled = os.environ.get("JEV_DECISION_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    # Also allow shadow flag as consult signal without making shadow authoritative alone
    if not enabled:
        return decision

    try:
        from parrts.email.jev_shadow import classify_decision

        shadow = classify_decision(subject=query[:200], body=query, sender_email="")
    except Exception:
        return decision

    if not isinstance(shadow, dict):
        return decision

    decision.jev_consulted = True
    decision.jev_needs_human = bool(shadow.get("needs_human"))
    decision.jev_label = shadow.get("label")
    conf = shadow.get("choice_confidence")
    try:
        decision.jev_choice_confidence = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        decision.jev_choice_confidence = None
    decision.decision_source = "deterministic_policy+jev"

    # JEV may escalate RESOLVED → NEEDS_HUMAN; it may not invent a SKU resolve.
    if decision.outcome == "RESOLVED" and decision.jev_needs_human:
        decision.outcome = "NEEDS_HUMAN"
        decision.confidence = min(decision.confidence, 0.5)
        decision.evidence_sufficiency = "partial"
        decision.ambiguity_reason = (
            decision.ambiguity_reason
            or "JEV flagged operational risk requiring human review"
        )
        decision.recommended_action = (
            "Human review required (JEV risk gate). Keep the candidate SKU visible, "
            "but do not auto-quote without counter confirmation."
        )
    return decision


def build_unit_of_work(answer: Any) -> TransmissionUnitOfWork:
    """Build a unit of work from a TransmissionInquiryAnswer-like object."""
    evidence = TransmissionEvidence(
        query=getattr(answer, "query", "") or "",
        deterministic_status=getattr(answer, "status", "") or "",
        sku=getattr(answer, "sku", None),
        name=getattr(answer, "name", None),
        transmission_family=getattr(answer, "transmission_family", None),
        part_type=getattr(answer, "part_type", None),
        fitment_status=getattr(answer, "fitment_status", None),
        inventory_available=bool(getattr(answer, "inventory_available", False)),
        aggregate_available=int(getattr(answer, "aggregate_available", 0) or 0),
        inventory=list(getattr(answer, "inventory", None) or []),
        identifiers=list(getattr(answer, "identifiers", None) or []),
        interchanges=list(getattr(answer, "interchanges", None) or []),
        verification_status=getattr(answer, "verification_status", None),
        uncertainty=list(getattr(answer, "uncertainty", None) or []),
        matched_sku_count=(
            1
            if getattr(answer, "sku", None)
            else (0 if getattr(answer, "status", "") != "ambiguous" else 2)
        ),
    )
    decision = evaluate_evidence_policy(evidence)
    decision = _maybe_consult_jev(evidence.query, decision)

    return TransmissionUnitOfWork(
        request_id=str(uuid.uuid4()),
        created_at=_utcnow(),
        query=evidence.query,
        evidence=evidence,
        decision=decision,
        status=evidence.deterministic_status,
        sku=evidence.sku,
        human_readable=getattr(answer, "human_readable", "") or "",
    )


def persist_unit_of_work(
    root: Path | str | None,
    uow: TransmissionUnitOfWork,
) -> dict[str, Any] | None:
    """Best-effort automation-ledger record. Never raises. Never writes DMS."""
    if root is None:
        return None
    try:
        from parrts.automation.service import AutomationService

        detail = uow.to_dict()
        # Prefer request_id as source_ref so feedback can locate the row reliably.
        summary = (
            f"{uow.decision.outcome} conf={uow.decision.confidence:.2f} "
            f"status={uow.status} sku={uow.sku or '—'}"
        )
        run = AutomationService(root).record_run(
            kind=KIND,
            source_ref=uow.request_id,
            status="ok" if uow.decision.outcome == "RESOLVED" else "needs_human",
            summary=summary,
            detail=detail,
            requires_human=uow.decision.outcome == "NEEDS_HUMAN",
        )
        if isinstance(run, dict) and run.get("id") is not None:
            detail["automation_run_id"] = run["id"]
            try:
                import json

                svc = AutomationService(root)
                svc.store.execute(
                    "UPDATE automation_runs SET detail_json = ? WHERE id = ? AND kind = ?",
                    (json.dumps(detail), int(run["id"]), KIND),
                )
                svc.store.commit()
                run["detail"] = detail
            except Exception:
                pass
        return run
    except Exception as exc:
        logger.warning("transmission_uow_persist_failed: %s", exc)
        return None


def _detail_of(run: dict[str, Any]) -> dict[str, Any]:
    d = run.get("detail")
    if isinstance(d, dict):
        return dict(d)
    raw = run.get("detail_json")
    if isinstance(raw, str):
        import json

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def find_unit_of_work_run(
    root: Path | str,
    request_id: str,
    *,
    limit: int = 500,
) -> dict[str, Any] | None:
    """Locate a transmission_request_uow run by request_id. None if missing."""
    from parrts.automation.service import AutomationService

    rid = str(request_id or "").strip()
    if not rid:
        return None
    runs = AutomationService(root).list_runs(kind=KIND, limit=int(limit))
    for run in runs:
        d = _detail_of(run)
        if str(d.get("request_id") or "") == rid:
            return run
        if str(run.get("source_ref") or "") == rid:
            return run
    return None


def apply_human_feedback(
    root: Path | str,
    request_id: str,
    *,
    action: Literal["accept", "correct", "resolve"],
    final_sku: str | None = None,
    note: str | None = None,
    actor: str = "counter",
) -> dict[str, Any]:
    """
    Accept, correct, or manually resolve a transmission unit of work.

    Updates the existing automation ledger row in place. Never mutates DMS.
    Never creates a parallel feedback store.
    """
    import json

    from parrts.automation.service import AutomationService

    rid = str(request_id or "").strip()
    if not rid:
        return {
            "ok": False,
            "error": "request_id required",
            "final_result_recorded": False,
        }

    run = find_unit_of_work_run(root, rid)
    if run is None:
        return {
            "ok": False,
            "error": "request not found",
            "request_id": rid,
            "final_result_recorded": False,
        }

    run_id = int(run.get("id") or 0)
    detail = _detail_of(run)
    if detail.get("final_result_recorded"):
        return {
            "ok": False,
            "error": "final result already recorded",
            "request_id": rid,
            "automation_run_id": run_id,
            "final_result_recorded": True,
            "detail": detail,
        }

    system_outcome = detail.get("system_outcome") or detail.get("outcome")
    system_sku = detail.get("system_sku") if "system_sku" in detail else detail.get("sku")
    system_confidence = detail.get("system_confidence")
    if system_confidence is None:
        system_confidence = detail.get("confidence")
    system_status = detail.get("system_status") or detail.get("status")
    system_result = detail.get("system_result") or detail.get("human_readable")

    # Ensure immutable system snapshot is retained
    detail["system_outcome"] = system_outcome
    detail["system_sku"] = system_sku
    detail["system_confidence"] = system_confidence
    detail["system_status"] = system_status
    detail["system_result"] = system_result

    action_l = str(action or "").strip().lower()
    sku_in = (final_sku or "").strip() or None
    note_in = (note or "").strip() or None
    now = _utcnow()

    if action_l == "accept":
        if system_outcome != "RESOLVED":
            return {
                "ok": False,
                "error": "accept is only valid for RESOLVED system outcomes",
                "request_id": rid,
                "system_outcome": system_outcome,
                "final_result_recorded": False,
            }
        detail["human_override"] = False
        detail["final_accepted_outcome"] = "RESOLVED"
        detail["final_accepted_sku"] = system_sku
        detail["final_accepted_at"] = now
        detail["final_accepted_note"] = note_in
        detail["final_accepted_by"] = actor
        detail["final_result_recorded"] = True
        detail["feedback_action"] = "accept"
    elif action_l == "correct":
        if system_outcome != "RESOLVED":
            return {
                "ok": False,
                "error": "correct is only valid for RESOLVED system outcomes; use resolve for NEEDS_HUMAN",
                "request_id": rid,
                "system_outcome": system_outcome,
                "final_result_recorded": False,
            }
        if not sku_in:
            return {
                "ok": False,
                "error": "final_sku required for correct",
                "request_id": rid,
                "final_result_recorded": False,
            }
        detail["human_override"] = True
        detail["final_accepted_outcome"] = "RESOLVED"
        detail["final_accepted_sku"] = sku_in
        detail["final_accepted_at"] = now
        detail["final_accepted_note"] = note_in
        detail["final_accepted_by"] = actor
        detail["final_result_recorded"] = True
        detail["feedback_action"] = "correct"
        detail["original_system_sku"] = system_sku
        detail["original_system_outcome"] = system_outcome
    elif action_l == "resolve":
        if system_outcome == "RESOLVED" and not detail.get("human_override"):
            # Allow resolve on NEEDS_HUMAN primarily; if already RESOLVED without feedback,
            # treat like correct when sku provided, else reject.
            if not sku_in:
                return {
                    "ok": False,
                    "error": "resolve requires final_sku when system already RESOLVED; use accept or correct",
                    "request_id": rid,
                    "final_result_recorded": False,
                }
        if not sku_in:
            return {
                "ok": False,
                "error": "final_sku required to manually resolve",
                "request_id": rid,
                "final_result_recorded": False,
            }
        detail["human_override"] = True
        detail["final_accepted_outcome"] = "RESOLVED"
        detail["final_accepted_sku"] = sku_in
        detail["final_accepted_at"] = now
        detail["final_accepted_note"] = note_in
        detail["final_accepted_by"] = actor
        detail["final_result_recorded"] = True
        detail["feedback_action"] = "resolve"
        detail["original_system_sku"] = system_sku
        detail["original_system_outcome"] = system_outcome
    else:
        return {
            "ok": False,
            "error": f"unknown action: {action}",
            "request_id": rid,
            "final_result_recorded": False,
        }

    # Keep top-level mirrors for list/report consumers
    detail["outcome"] = detail.get("system_outcome")  # system decision stays
    detail["sku"] = detail.get("system_sku")
    detail["human_feedback_at"] = now

    summary = (
        f"FINAL {detail['final_accepted_outcome']} "
        f"sku={detail.get('final_accepted_sku') or '—'} "
        f"override={detail.get('human_override')} "
        f"action={detail.get('feedback_action')}"
    )

    svc = AutomationService(root)
    svc.store.execute(
        """
        UPDATE automation_runs
        SET detail_json = ?, summary = ?, status = ?, requires_human = ?
        WHERE id = ? AND kind = ?
        """,
        (
            json.dumps(detail),
            summary,
            "finalized",
            0,
            run_id,
            KIND,
        ),
    )
    # Verify row count — do not silently update wrong kinds
    row = svc.store.fetchone(
        "SELECT id, kind, detail_json, summary, status FROM automation_runs WHERE id = ?",
        (run_id,),
    )
    svc.store.commit()
    if row is None or str(row["kind"]) != KIND:
        return {
            "ok": False,
            "error": "update target mismatch",
            "request_id": rid,
            "final_result_recorded": False,
        }

    return {
        "ok": True,
        "request_id": rid,
        "automation_run_id": run_id,
        "final_result_recorded": True,
        "human_override": detail.get("human_override"),
        "final_accepted_outcome": detail.get("final_accepted_outcome"),
        "final_accepted_sku": detail.get("final_accepted_sku"),
        "final_accepted_at": detail.get("final_accepted_at"),
        "final_accepted_note": detail.get("final_accepted_note"),
        "system_outcome": detail.get("system_outcome"),
        "system_sku": detail.get("system_sku"),
        "system_confidence": detail.get("system_confidence"),
        "feedback_action": detail.get("feedback_action"),
        "detail": detail,
    }
