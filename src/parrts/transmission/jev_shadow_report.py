"""Read-only analysis of transmission JEV shadow observations.

Observations live in the existing automation ledger
(``.parrts/automation.db``), kind ``transmission_jev_shadow``.

This module never calls JEV/TypeSafe and never mutates DMS.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from parrts.automation.service import AutomationService

KIND = "transmission_jev_shadow"
SCHEMA_VERSION = "transmission_jev_shadow.v1"


def _detail(run: dict[str, Any]) -> dict[str, Any]:
    d = run.get("detail")
    return d if isinstance(d, dict) else {}


def build_transmission_jev_shadow_report(
    root: Path | str,
    *,
    limit: int = 500,
    recent: int = 20,
) -> dict[str, Any]:
    """Aggregate persisted shadow observations into a structured report.

    Does not contact JEV. Does not mutate DMS or the automation ledger.
    """
    svc = AutomationService(root)
    runs = svc.list_runs(kind=KIND, limit=int(limit))

    total = len(runs)
    result_count = 0
    no_result_count = 0
    error_count = 0

    det_status_counts: dict[str, int] = {}
    jev_label_counts: dict[str, int] = {}
    needs_human_counts = {"true": 0, "false": 0, "unknown": 0}
    confidences: list[float] = []
    cross_tab: dict[str, dict[str, int]] = {}
    det_needs_human: dict[str, dict[str, int]] = {}
    resolved_with_stock = 0
    resolved_zero_stock = 0
    review_candidates = {
        "resolved_needs_human": 0,
        "unresolved_no_human": 0,
    }

    for run in runs:
        d = _detail(run)
        eval_status = d.get("jev_evaluation_status")
        if eval_status not in ("result", "no_result", "error"):
            # Fall back to automation run status
            rs = run.get("status")
            if rs == "ok":
                eval_status = "result"
            elif rs == "no_result":
                eval_status = "no_result"
            elif rs == "error":
                eval_status = "error"
            else:
                eval_status = "no_result"

        if eval_status == "result":
            result_count += 1
        elif eval_status == "error":
            error_count += 1
        else:
            no_result_count += 1
            eval_status = "no_result"

        det = str(d.get("deterministic_status") or "unknown")
        det_status_counts[det] = det_status_counts.get(det, 0) + 1

        label = d.get("jev_label")
        label_key = str(label) if label is not None else "(none)"
        if eval_status == "result":
            jev_label_counts[label_key] = jev_label_counts.get(label_key, 0) + 1

        nh = d.get("jev_needs_human")
        if nh is True:
            needs_human_counts["true"] += 1
            nh_key = "true"
        elif nh is False:
            needs_human_counts["false"] += 1
            nh_key = "false"
        else:
            needs_human_counts["unknown"] += 1
            nh_key = "unknown"

        conf = d.get("jev_choice_confidence")
        if isinstance(conf, (int, float)):
            confidences.append(float(conf))

        # Cross-tab: deterministic_status -> JEV label
        cross_tab.setdefault(det, {})
        cross_tab[det][label_key] = cross_tab[det].get(label_key, 0) + 1

        # deterministic_status -> needs_human
        det_needs_human.setdefault(det, {"true": 0, "false": 0, "unknown": 0})
        det_needs_human[det][nh_key] = det_needs_human[det].get(nh_key, 0) + 1

        if det == "resolved":
            inv_avail = d.get("deterministic_inventory_available")
            agg = d.get("deterministic_aggregate_available")
            if inv_avail is True or (isinstance(agg, (int, float)) and agg > 0):
                resolved_with_stock += 1
            elif inv_avail is False or agg == 0:
                resolved_zero_stock += 1

        # Neutral review candidates (not errors)
        if det == "resolved" and nh is True:
            review_candidates["resolved_needs_human"] += 1
        if det in ("ambiguous", "no_match", "insufficient") and nh is False:
            review_candidates["unresolved_no_human"] += 1

    confidence_stats: dict[str, Any]
    if confidences:
        confidence_stats = {
            "count": len(confidences),
            "minimum": min(confidences),
            "mean": sum(confidences) / len(confidences),
            "maximum": max(confidences),
            "note": "confidence is not accuracy; taxonomies are not equivalent",
        }
    else:
        confidence_stats = {
            "count": 0,
            "minimum": None,
            "mean": None,
            "maximum": None,
            "note": "confidence is not accuracy; taxonomies are not equivalent",
        }

    recent_obs = []
    for run in runs[: max(0, int(recent))]:
        d = _detail(run)
        recent_obs.append(
            {
                "id": run.get("id"),
                "created_at": run.get("created_at"),
                "status": run.get("status"),
                "summary": run.get("summary"),
                "source_ref": run.get("source_ref"),
                "requires_human": run.get("requires_human"),
                "query": d.get("query"),
                "deterministic_status": d.get("deterministic_status"),
                "deterministic_sku": d.get("deterministic_sku"),
                "jev_evaluation_status": d.get("jev_evaluation_status"),
                "jev_label": d.get("jev_label"),
                "jev_needs_human": d.get("jev_needs_human"),
                "jev_choice_confidence": d.get("jev_choice_confidence"),
            }
        )

    return {
        "ok": True,
        "kind": KIND,
        "schema": SCHEMA_VERSION,
        "limit": int(limit),
        "volume": {
            "total": total,
            "result": result_count,
            "no_result": no_result_count,
            "error": error_count,
        },
        "deterministic_outcomes": det_status_counts,
        "jev_intent_labels": jev_label_counts,
        "needs_human": needs_human_counts,
        "confidence": confidence_stats,
        "cross_tab_deterministic_status_to_jev_label": cross_tab,
        "cross_tab_deterministic_status_to_needs_human": det_needs_human,
        "inventory_context": {
            "resolved_with_stock": resolved_with_stock,
            "resolved_zero_stock": resolved_zero_stock,
        },
        "review_candidates": {
            **review_candidates,
            "note": (
                "Neutral review signals only — not JEV errors or accuracy scores. "
                "Deterministic status and JEV label answer different questions."
            ),
        },
        "recent_observations": recent_obs,
        "notes": [
            "Deterministic transmission statuses and JEV labels are separate taxonomies.",
            "Do not treat label match rates as accuracy.",
            "This report is read-only over the automation ledger.",
        ],
    }


def persist_transmission_jev_shadow_observation(
    root: Path | str,
    *,
    query: str,
    answer: Any,
    jev_evaluation_status: str,
    shadow: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Best-effort write one shadow observation to the automation ledger.

    Never raises. Returns the recorded run dict or None on failure.
    """
    try:
        from parrts.automation.service import AutomationService

        detail: dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "query": query,
            "deterministic_status": getattr(answer, "status", None),
            "deterministic_sku": getattr(answer, "sku", None),
            "deterministic_inventory_available": getattr(
                answer, "inventory_available", None
            ),
            "deterministic_aggregate_available": getattr(
                answer, "aggregate_available", None
            ),
            "deterministic_fitment_status": getattr(answer, "fitment_status", None),
            "deterministic_verification_status": getattr(
                answer, "verification_status", None
            ),
            "jev_evaluation_status": jev_evaluation_status,
        }

        requires_human = False
        run_status = "ok"
        label = None

        if jev_evaluation_status == "result" and isinstance(shadow, dict):
            label = shadow.get("label")
            detail["jev_label"] = label
            detail["jev_choice_confidence"] = shadow.get("choice_confidence")
            detail["jev_needs_human"] = shadow.get("needs_human")
            detail["jev_noul_probability"] = shadow.get("noul_probability")
            detail["jev_model"] = shadow.get("model")
            requires_human = bool(shadow.get("needs_human"))
            run_status = "ok"
        elif jev_evaluation_status == "no_result":
            run_status = "no_result"
        elif jev_evaluation_status == "error":
            run_status = "error"
            if error:
                detail["error"] = str(error)[:500]
        else:
            run_status = str(jev_evaluation_status)

        det_status = getattr(answer, "status", None) or "unknown"
        if jev_evaluation_status == "result" and label:
            summary = f"{det_status} -> {label}"
        else:
            summary = f"{det_status} -> {jev_evaluation_status}"

        sku = getattr(answer, "sku", None)
        source_ref = sku if sku else f"{det_status}:{query[:80]}"

        svc = AutomationService(root)
        return svc.record_run(
            kind=KIND,
            source_ref=source_ref,
            status=run_status,
            summary=summary,
            detail=detail,
            requires_human=requires_human,
        )
    except Exception:
        return None
