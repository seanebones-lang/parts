"""Counter search orchestrator: frozen resolver + inventory discovery.

Modes:
  exact_match       — one safe SKU (resolver or exact catalog SKU)
  inventory_matches — clear product class / multi-lot identifier → browse lots
  needs_review      — genuine safety / identity uncertainty

Does not change resolver.py or decision.py semantics.
Eval paths should continue calling answer_transmission_inquiry directly.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from parrts.dms.service import DmsService

from .discovery import (
    discover_by_identifier,
    discover_inventory,
    families_in_query,
    normalize_query,
    part_category_in_query,
)
from .resolver import competing_signal_reason, resolve_inquiry
from .service import TransmissionInquiryAnswer, answer_transmission_inquiry

SearchMode = Literal["exact_match", "inventory_matches", "needs_review"]


@dataclass
class CounterSearchResult:
    query: str
    search_mode: SearchMode
    # Mirror inquiry fields for FE compatibility
    status: str = "insufficient"
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
    human_readable: str = ""
    uncertainty: list[str] = field(default_factory=list)
    # Unit-of-work (only populated for exact_match / needs_review from resolver path)
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
    # Discovery payload
    discovery: dict[str, Any] | None = None
    elapsed_ms: float = 0.0

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "search_mode": self.search_mode,
            "status": self.status,
            "sku": self.sku,
            "name": self.name,
            "transmission_family": self.transmission_family,
            "part_type": self.part_type,
            "fitment_status": self.fitment_status,
            "inventory_available": self.inventory_available,
            "aggregate_available": self.aggregate_available,
            "verification_status": self.verification_status,
            "human_readable": self.human_readable,
            "inventory": self.inventory,
            "identifiers": self.identifiers,
            "interchanges": self.interchanges,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action,
            "ambiguity_reason": self.ambiguity_reason,
            "intent": self.intent,
            "candidate_match_quality": self.candidate_match_quality,
            "evidence_sufficiency": self.evidence_sufficiency,
            "decision_source": self.decision_source,
            "request_id": self.request_id,
            "decision": self.decision,
            "discovery": self.discovery,
            "elapsed_ms": self.elapsed_ms,
        }


def _from_answer(answer: TransmissionInquiryAnswer, mode: SearchMode, elapsed_ms: float) -> CounterSearchResult:
    return CounterSearchResult(
        query=answer.query,
        search_mode=mode,
        status=answer.status,
        sku=answer.sku,
        name=answer.name,
        transmission_family=answer.transmission_family,
        part_type=answer.part_type,
        fitment_status=answer.fitment_status,
        inventory=list(answer.inventory or []),
        aggregate_available=int(answer.aggregate_available or 0),
        inventory_available=bool(answer.inventory_available),
        identifiers=list(answer.identifiers or []),
        interchanges=list(answer.interchanges or []),
        verification_status=answer.verification_status,
        human_readable=answer.human_readable or "",
        uncertainty=list(answer.uncertainty or []),
        outcome=answer.outcome,
        confidence=answer.confidence,
        recommended_action=answer.recommended_action,
        ambiguity_reason=answer.ambiguity_reason,
        intent=answer.intent,
        candidate_match_quality=answer.candidate_match_quality,
        evidence_sufficiency=answer.evidence_sufficiency,
        decision_source=answer.decision_source,
        request_id=answer.request_id,
        decision=answer.decision,
        elapsed_ms=elapsed_ms,
    )


def _looks_like_exact_sku(q: str) -> str | None:
    raw = (q or "").strip()
    if not raw or " " in raw:
        return None
    # SKU-ish tokens
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._\-/]{2,63}", raw):
        return raw
    return None


def _looks_like_identifier_token(q: str) -> str | None:
    raw = (q or "").strip()
    if not raw or " " in raw:
        return None
    # Pure identifier: mostly digits or OEM-like, not a transmission family token
    if families_in_query(raw):
        return None
    if part_category_in_query(raw):
        return None
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-]{3,47}", raw):
        return raw
    return None


def _inventory_match_result(
    query: str,
    disc,
    *,
    elapsed_ms: float,
    reason: str,
) -> CounterSearchResult:
    family = disc.family
    part = disc.part_category
    hr = (
        f"{family or ''} {part or 'parts'}".strip()
        + f" — {disc.candidate_count} inventory lot(s), "
        + f"{disc.total_available} available across locations. "
        + "Select a sellable unit to quote or reserve."
    )
    return CounterSearchResult(
        query=query,
        search_mode="inventory_matches",
        status="inventory_matches",
        transmission_family=family,
        part_type=part,
        aggregate_available=disc.total_available,
        inventory_available=disc.total_available > 0,
        human_readable=hr,
        # Not an autonomous exact resolve — discovery browse
        outcome=None,
        confidence=None,
        recommended_action="Select a matching inventory lot, then Add to Quote or Reserve.",
        ambiguity_reason=None,
        intent="inventory_browse",
        candidate_match_quality="class_match",
        evidence_sufficiency="sufficient_for_browse",
        decision_source="inventory_discovery",
        discovery=disc.to_dict(),
        uncertainty=[reason] if reason else [],
        elapsed_ms=elapsed_ms,
    )


def _needs_review_from_answer(answer: TransmissionInquiryAnswer, elapsed_ms: float) -> CounterSearchResult:
    r = _from_answer(answer, "needs_review", elapsed_ms)
    if not r.outcome:
        r.outcome = "NEEDS_HUMAN"
    return r


def counter_search(query: str, dms: DmsService) -> CounterSearchResult:
    """JP counter entry: exact / inventory browse / needs review."""
    t0 = time.perf_counter()
    q = (query or "").strip()
    if len(q) < 2:
        elapsed = (time.perf_counter() - t0) * 1000
        return CounterSearchResult(
            query=q,
            search_mode="needs_review",
            status="insufficient",
            human_readable="Enter a longer search.",
            outcome="NEEDS_HUMAN",
            elapsed_ms=elapsed,
        )

    # --- Exact catalog SKU ---
    sku_tok = _looks_like_exact_sku(q)
    if sku_tok:
        row = dms.store.fetchone(
            "SELECT sku FROM catalog_parts WHERE UPPER(sku) = UPPER(?)",
            (sku_tok,),
        )
        if row is not None:
            answer = answer_transmission_inquiry(str(row["sku"]), dms)
            elapsed = (time.perf_counter() - t0) * 1000
            # Force exact path even if dense catalog confuses bare resolve
            if answer.status == "resolved" and answer.sku:
                return _from_answer(answer, "exact_match", elapsed)
            # Still one catalog SKU — load inventory for that SKU as exact
            disc = discover_inventory(
                dms, family=None, part_category=None, sku_filter=[str(row["sku"])]
            )
            if disc.candidate_count == 1 or (
                disc.candidate_count >= 1 and len({c.sku for c in disc.candidates}) == 1
            ):
                answer2 = answer_transmission_inquiry(str(row["sku"]), dms)
                # Build exact manually if resolver multi-hit on SKU token
                from .repository import TransmissionRepository

                repo = TransmissionRepository(dms)
                inv = repo.get_inventory(str(row["sku"]))
                idents = repo.get_identifiers(str(row["sku"]))
                inter = repo.get_interchanges(str(row["sku"]))
                cat = dms.store.fetchone(
                    "SELECT name, transmission_family, verification_status FROM catalog_parts WHERE sku = ?",
                    (str(row["sku"]),),
                )
                agg = sum(int(r.get("qty") or 0) for r in inv)
                elapsed = (time.perf_counter() - t0) * 1000
                return CounterSearchResult(
                    query=q,
                    search_mode="exact_match",
                    status="resolved",
                    sku=str(row["sku"]),
                    name=str(cat["name"]) if cat else None,
                    transmission_family=str(cat["transmission_family"]) if cat else None,
                    inventory=inv,
                    identifiers=idents,
                    interchanges=inter,
                    aggregate_available=agg,
                    inventory_available=agg > 0,
                    verification_status=str(cat["verification_status"]) if cat else None,
                    human_readable=f"Exact SKU {row['sku']}.",
                    outcome="RESOLVED",
                    confidence=0.99,
                    recommended_action="Add to quote or reserve this SKU.",
                    intent="exact_sku",
                    candidate_match_quality="exact",
                    evidence_sufficiency="sufficient",
                    decision_source="exact_sku_lookup",
                    elapsed_ms=elapsed,
                )

    # --- Identifier-only token (casting/OEM) ---
    id_tok = _looks_like_identifier_token(q)
    if id_tok:
        disc = discover_by_identifier(dms, id_tok)
        elapsed = (time.perf_counter() - t0) * 1000
        skus = {c.sku for c in disc.candidates}
        if len(skus) == 1:
            only = next(iter(skus))
            answer = answer_transmission_inquiry(only, dms)
            if answer.status == "resolved":
                return _from_answer(answer, "exact_match", elapsed)
            # single SKU exact construct
            return counter_search(only, dms)  # re-enter as SKU
        if len(skus) > 1:
            disc.notes.append(f"identifier {id_tok!r} matches multiple inventory lots")
            return _inventory_match_result(
                q, disc, elapsed_ms=elapsed, reason="multi_lot_identifier"
            )
        # fall through if no identifier hits

    # --- Safety: competing signals (frozen helper) ---
    fams = families_in_query(q)
    compete = competing_signal_reason(normalize_query(q), fams)
    if compete:
        answer = answer_transmission_inquiry(q, dms)
        elapsed = (time.perf_counter() - t0) * 1000
        return _needs_review_from_answer(answer, elapsed)

    # --- Frozen resolver ---
    low = resolve_inquiry(q, dms)

    # Vehicle / fitment safety from frozen resolver — do not browse past it
    unc = " ".join(low.uncertainty or []).lower()
    fit_unsafe = (
        low.fitment_status in ("insufficient", "no_match")
        and any(
            m in unc
            for m in (
                "fitment",
                "vehicle",
                "conflict",
                "prius",
                "could not be verified",
            )
        )
    )
    if fit_unsafe or any(
        m in unc
        for m in (
            "vehicle/transmission fitment could not be verified",
            "stated family conflicts",
            "vehicle implies",
        )
    ):
        answer = answer_transmission_inquiry(q, dms)
        elapsed = (time.perf_counter() - t0) * 1000
        return _needs_review_from_answer(answer, elapsed)

    # Single SKU from resolver → exact
    if len(low.matched_skus) == 1:
        answer = answer_transmission_inquiry(q, dms)
        elapsed = (time.perf_counter() - t0) * 1000
        if answer.status == "resolved":
            return _from_answer(answer, "exact_match", elapsed)

    # Multi SKU from resolver (e.g. multi identifier) → inventory lots for those SKUs
    if len(low.matched_skus) > 1:
        # If competing already handled; this is multi-lot not cross-family conflict
        cat = part_category_in_query(q) or low.part_type
        # Explicit single family token in the query → isolate that variant
        qv = fams[0] if len(fams) == 1 else None
        disc = discover_inventory(
            dms,
            family=None,
            part_category=cat,
            sku_filter=list(low.matched_skus),
            query_variant=qv,
        )
        if disc.candidate_count > 0:
            elapsed = (time.perf_counter() - t0) * 1000
            if not disc.part_category:
                disc.part_category = cat
            if not disc.family and fams:
                disc.family = fams[0]
            if qv and not disc.family:
                disc.family = qv
            return _inventory_match_result(
                q, disc, elapsed_ms=elapsed, reason="resolver_multi_sku"
            )
        # multi SKU but none survive category/variant filter → fall through to class discovery

    # Resolver uncertainty that is true conflict (vehicle etc.) without clear single class
    uncertainty = " ".join(low.uncertainty or []).lower()
    unsafe_markers = (
        "conflict",
        "competing",
        "cannot return a single",
        "fitment could not be verified",
        "vehicle/transmission",
        "instead of",
        "which one",
    )
    if any(m in uncertainty for m in unsafe_markers) and not (
        families_in_query(q) and part_category_in_query(q)
    ):
        answer = answer_transmission_inquiry(q, dms)
        elapsed = (time.perf_counter() - t0) * 1000
        return _needs_review_from_answer(answer, elapsed)

    # --- Discovery product class ---
    family = (fams[0] if fams else None) or low.transmission_family
    category = part_category_in_query(q) or low.part_type
    # Map resolver pump/valve body/drum already normalized
    if category in ("pump", "valve body", "drum") or category:
        if family and category:
            # Multi-family without competition already returned; if 2+ families stated bare:
            if len(fams) >= 2:
                answer = answer_transmission_inquiry(q, dms)
                elapsed = (time.perf_counter() - t0) * 1000
                return _needs_review_from_answer(answer, elapsed)
            disc = discover_inventory(
                dms,
                family=family,
                part_category=category,
                query_variant=family,
            )
            elapsed = (time.perf_counter() - t0) * 1000
            if disc.candidate_count > 0:
                return _inventory_match_result(
                    q, disc, elapsed_ms=elapsed, reason="product_class_match"
                )
            # clear class but empty stock
            return CounterSearchResult(
                query=q,
                search_mode="needs_review",
                status="no_match",
                transmission_family=family,
                part_type=category,
                human_readable=f"No inventory lots for {family} {category}.",
                outcome="NEEDS_HUMAN",
                recommended_action="Try another family/part type or check Data Import seed.",
                decision_source="inventory_discovery",
                discovery=disc.to_dict(),
                elapsed_ms=elapsed,
            )

    # Fallback: existing inquiry answer
    answer = answer_transmission_inquiry(q, dms)
    elapsed = (time.perf_counter() - t0) * 1000
    if answer.status == "resolved":
        return _from_answer(answer, "exact_match", elapsed)
    return _needs_review_from_answer(answer, elapsed)
