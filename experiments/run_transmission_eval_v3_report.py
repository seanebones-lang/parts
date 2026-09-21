#!/usr/bin/env python3
"""Eval v3 report — real JP counter holdout from transmission_request_uow ledger.

Read-only. Does not change resolver, decision policy, or JEV authority.
Does not create a parallel evaluation database.

  PYTHONPATH=src:backend:experiments \\
    python experiments/run_transmission_eval_v3_report.py --root .

Optional window:
  --since 2026-09-21T00:00:00+00:00
  --until 2026-10-21T00:00:00+00:00

Writes:
  experiments/transmission_eval_v3_results.json
  experiments/transmission_eval_v3_report.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).resolve().parent / "transmission_eval_v3_baseline.json"
KIND = "transmission_request_uow"
SHADOW_KIND = "transmission_jev_shadow"

# Lightweight PII scrub for notes/summaries in shared reports (not a full DLP system)
_PII_PATTERNS = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _scrub(text: str | None) -> str | None:
    if text is None:
        return None
    s = str(text)
    for pat in _PII_PATTERNS:
        s = pat.sub("[REDACTED]", s)
    return s


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    t = str(s).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _load_baseline() -> dict[str, Any]:
    if BASELINE_PATH.is_file():
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {
        "frozen_sut_sha": "932af65d58201a3e2be50fa4ed9262f136ce3598",
        "status": "collection_open",
    }


def _detail(run: dict[str, Any]) -> dict[str, Any]:
    raw = run.get("detail_json") or run.get("detail") or {}
    if isinstance(raw, str):
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _evidence_query(detail: dict[str, Any]) -> str:
    ev = detail.get("evidence")
    if isinstance(ev, dict) and ev.get("query"):
        return str(ev.get("query"))
    for k in ("raw_query", "query", "original_query"):
        if detail.get(k):
            return str(detail.get(k))
    return ""


def load_uow_runs(root: Path, *, limit: int = 5000) -> list[dict[str, Any]]:
    from parrts.automation.service import AutomationService

    svc = AutomationService(root)
    runs = svc.list_runs(kind=KIND, limit=limit)
    # list_runs may already parse detail; normalize
    out: list[dict[str, Any]] = []
    for r in runs:
        row = dict(r)
        if "detail" not in row and "detail_json" in row:
            row["detail"] = _detail(row)
        elif "detail" in row and isinstance(row["detail"], str):
            row["detail"] = _detail({"detail_json": row["detail"]})
        out.append(row)
    return out


def load_shadow_runs(root: Path, *, limit: int = 5000) -> list[dict[str, Any]]:
    from parrts.automation.service import AutomationService

    try:
        return [dict(r) for r in AutomationService(root).list_runs(kind=SHADOW_KIND, limit=limit)]
    except Exception:
        return []


def in_window(ts: str | None, since: datetime | None, until: datetime | None) -> bool:
    dt = _parse_ts(ts)
    if dt is None:
        # keep rows with unknown ts only if no window bound
        return since is None and until is None
    if since is not None and dt < since:
        return False
    if until is not None and dt >= until:
        return False
    return True


def classify_row(detail: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    """Map one uow ledger row to an Eval v3 record + verdict."""
    system_outcome = detail.get("system_outcome") or detail.get("outcome")
    system_sku = detail.get("system_sku") if "system_sku" in detail else detail.get("sku")
    finalized = bool(detail.get("final_result_recorded"))
    feedback = detail.get("feedback_action")
    override = detail.get("human_override")
    final_sku = detail.get("final_accepted_sku")
    final_outcome = detail.get("final_accepted_outcome")

    verdict = "pending_feedback"
    if finalized:
        if system_outcome == "RESOLVED" and override is False and feedback == "accept":
            verdict = "accept"
        elif system_outcome == "RESOLVED" and (
            override is True or (final_sku and final_sku != system_sku)
        ):
            verdict = "false_resolution"
        elif system_outcome == "NEEDS_HUMAN" and feedback == "resolve" and final_sku:
            verdict = "missed_resolution"  # human could resolve what system escalated
        elif system_outcome == "NEEDS_HUMAN" and not final_sku:
            verdict = "escalated_unresolved"
        elif system_outcome == "NEEDS_HUMAN" and finalized:
            verdict = "escalated_resolved_by_human"
        else:
            verdict = "other_finalized"
    elif str(run.get("status") or "") == "finalized":
        verdict = "finalized_without_flag"
    elif int(run.get("requires_human") or 0) == 1 or system_outcome == "NEEDS_HUMAN":
        verdict = "pending_human"
    else:
        verdict = "pending_feedback"

    return {
        "automation_run_id": run.get("id"),
        "request_id": detail.get("request_id") or run.get("source_ref"),
        "raw_query": _scrub(_evidence_query(detail)),
        "created_at": run.get("created_at"),
        "system_outcome": system_outcome,
        "system_sku": system_sku,
        "confidence": detail.get("system_confidence")
        if detail.get("system_confidence") is not None
        else detail.get("confidence"),
        "candidate_match_quality": detail.get("candidate_match_quality"),
        "evidence_sufficiency": detail.get("evidence_sufficiency"),
        "ambiguity_reason": _scrub(detail.get("ambiguity_reason")),
        "recommended_action": _scrub(detail.get("recommended_action")),
        "decision_source": detail.get("decision_source"),
        "feedback_action": feedback,
        "final_accepted_outcome": final_outcome,
        "final_accepted_sku": final_sku,
        "human_override": override,
        "final_accepted_note": _scrub(detail.get("final_accepted_note")),
        "final_result_recorded": finalized,
        "verdict": verdict,
        "status": run.get("status"),
    }


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    resolved = [r for r in rows if r.get("system_outcome") == "RESOLVED"]
    needs = [r for r in rows if r.get("system_outcome") == "NEEDS_HUMAN"]
    with_feedback = [r for r in rows if r.get("final_result_recorded")]
    accepts = [r for r in rows if r.get("verdict") == "accept"]
    false_res = [r for r in rows if r.get("verdict") == "false_resolution"]
    missed = [r for r in rows if r.get("verdict") == "missed_resolution"]
    overrides = [r for r in with_feedback if r.get("human_override") is True]
    unresolved = [
        r
        for r in rows
        if r.get("verdict") in ("pending_feedback", "pending_human", "escalated_unresolved")
    ]

    # Precision only over RESOLVED that received final feedback
    resolved_final = [
        r
        for r in resolved
        if r.get("final_result_recorded")
        and r.get("verdict") in ("accept", "false_resolution")
    ]
    accepted_resolved = [r for r in resolved_final if r.get("verdict") == "accept"]
    precision = (
        (len(accepted_resolved) / len(resolved_final)) if resolved_final else None
    )

    return {
        "total": n,
        "resolved_count": len(resolved),
        "needs_human_count": len(needs),
        "with_feedback_count": len(with_feedback),
        "resolved_with_feedback_count": len(resolved_final),
        "resolved_precision": precision,
        "false_resolution_count": len(false_res),
        "false_resolution_ids": [r.get("request_id") for r in false_res],
        "false_resolution_queries": [r.get("raw_query") for r in false_res],
        "missed_resolution_count": len(missed),
        "missed_resolution_ids": [r.get("request_id") for r in missed],
        "autonomous_accepted_count": len(accepts),
        "autonomous_accepted_coverage": (len(accepts) / n) if n else 0.0,
        "human_escalation_rate": (len(needs) / n) if n else 0.0,
        "override_rate": (len(overrides) / len(with_feedback)) if with_feedback else None,
        "unresolved_or_pending_count": len(unresolved),
        "verdict_counts": dict(Counter(r.get("verdict") for r in rows)),
    }


def correlate_shadow(
    rows: list[dict[str, Any]], shadow_runs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Best-effort: match shadow by query text for false-resolution cases."""
    by_query: dict[str, list[dict[str, Any]]] = {}
    for s in shadow_runs:
        d = _detail(s)
        q = str(d.get("query") or "").strip()
        if not q:
            continue
        by_query.setdefault(q, []).append(d)

    observations: list[dict[str, Any]] = []
    for r in rows:
        if r.get("verdict") != "false_resolution":
            continue
        q = str(r.get("raw_query") or "").strip()
        hits = by_query.get(q) or []
        if not hits:
            observations.append(
                {
                    "request_id": r.get("request_id"),
                    "raw_query": q,
                    "shadow": None,
                    "note": "no shadow row matched on raw query",
                }
            )
            continue
        d = hits[-1]
        would_escalate = bool(d.get("jev_needs_human"))
        observations.append(
            {
                "request_id": r.get("request_id"),
                "raw_query": q,
                "shadow_jev_needs_human": would_escalate,
                "shadow_jev_label": d.get("jev_label"),
                "would_have_caught_false_resolve": would_escalate,
            }
        )
    return observations


def render_report(
    *,
    baseline: dict[str, Any],
    root: str,
    metrics: dict[str, Any],
    rows: list[dict[str, Any]],
    shadow_obs: list[dict[str, Any]],
    since: str | None,
    until: str | None,
) -> str:
    lines: list[str] = []
    lines.append("# Transmission Counter Evaluation v3 — Real JP holdout")
    lines.append("")
    lines.append(f"- Generated: `{_utcnow()}`")
    lines.append(f"- Frozen SUT: `{baseline.get('frozen_sut_sha')}`")
    lines.append(f"- Ledger root: `{root}`")
    lines.append(f"- Source: `automation_runs.kind={KIND}`")
    lines.append(f"- Window since: `{since or 'open'}`")
    lines.append(f"- Window until: `{until or 'open'}`")
    lines.append(f"- Status: `{baseline.get('status', 'collection_open')}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- **Real requests in window:** {metrics['total']}")
    lines.append(f"- RESOLVED (system): {metrics['resolved_count']}")
    lines.append(f"- NEEDS_HUMAN (system): {metrics['needs_human_count']}")
    lines.append(f"- With human final feedback: {metrics['with_feedback_count']}")
    lines.append("")
    if metrics["total"] == 0:
        lines.append("## Status")
        lines.append("")
        lines.append(
            "No `transmission_request_uow` rows in this root/window. "
            "Collection is open. Production behavior remains frozen. "
            "Do not add synthetic Eval v3 cases."
        )
        lines.append("")
        lines.append("## Next")
        lines.append("")
        lines.append(
            "Run the pilot counter against the frozen SUT; ensure Accept/Correct/Resolve "
            "is used so precision is measurable. Re-run this report after ≥50 finalized rows when possible."
        )
        lines.append("")
        return "\n".join(lines)

    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    rp = metrics["resolved_precision"]
    lines.append(
        f"| Resolved precision | {rp if rp is None else f'{rp:.3f}'} |"
    )
    lines.append(f"| False-resolution count | {metrics['false_resolution_count']} |")
    lines.append(
        f"| Autonomous accepted coverage | {metrics['autonomous_accepted_coverage']:.3f} |"
    )
    lines.append(f"| Escalation rate | {metrics['human_escalation_rate']:.3f} |")
    ov = metrics["override_rate"]
    lines.append(f"| Override rate | {ov if ov is None else f'{ov:.3f}'} |")
    lines.append(f"| Missed-resolution count | {metrics['missed_resolution_count']} |")
    lines.append(
        f"| Unresolved/pending count | {metrics['unresolved_or_pending_count']} |"
    )
    lines.append("")
    lines.append("## False RESOLVED (highest severity)")
    lines.append("")
    if not metrics["false_resolution_count"]:
        lines.append("- none in window")
    else:
        for r in rows:
            if r.get("verdict") != "false_resolution":
                continue
            lines.append(
                f"- `{r.get('request_id')}` raw=`{r.get('raw_query')}` "
                f"system={r.get('system_sku')} final={r.get('final_accepted_sku')} "
                f"note=`{r.get('final_accepted_note') or ''}`"
            )
    lines.append("")
    lines.append("## Overrides / human corrections")
    lines.append("")
    overs = [r for r in rows if r.get("human_override") is True]
    if not overs:
        lines.append("- none")
    else:
        for r in overs:
            lines.append(
                f"- `{r.get('request_id')}` action={r.get('feedback_action')} "
                f"system={r.get('system_outcome')}/{r.get('system_sku')} "
                f"→ final={r.get('final_accepted_sku')} raw=`{r.get('raw_query')}`"
            )
    lines.append("")
    lines.append("## Representative raw counter language (up to 15)")
    lines.append("")
    shown = 0
    for r in rows:
        q = (r.get("raw_query") or "").strip()
        if not q:
            continue
        lines.append(f"- `{q}` → {r.get('system_outcome')}/{r.get('system_sku')} [{r.get('verdict')}]")
        shown += 1
        if shown >= 15:
            break
    if shown == 0:
        lines.append("- none")
    lines.append("")
    lines.append("## JEV shadow vs false RESOLVED")
    lines.append("")
    if not shadow_obs:
        lines.append("- no false RESOLVED to correlate, or shadow empty")
    else:
        for o in shadow_obs:
            lines.append(f"- {o}")
    lines.append("")
    lines.append("## Failure classes")
    lines.append("")
    lines.append(
        "Grouped only after the collection window closes with sufficient N. "
        "Do not invent categories in advance."
    )
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    if metrics["total"] < 50:
        lines.append(
            f"Sample size {metrics['total']} < 50 — keep collecting; do not change the resolver."
        )
    else:
        lines.append(
            "Sufficient N reached — review false RESOLVED and overrides; "
            "propose the smallest next eng change from observed failures only; do not implement until review."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval v3 real-holdout report from uow ledger")
    ap.add_argument("--root", default=str(ROOT), help="PARTS pilot root containing .parrts/")
    ap.add_argument("--since", default=None, help="ISO8601 inclusive lower bound on created_at")
    ap.add_argument("--until", default=None, help="ISO8601 exclusive upper bound on created_at")
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()

    baseline = _load_baseline()
    root = Path(args.root).resolve()
    since = _parse_ts(args.since)
    until = _parse_ts(args.until)

    runs = load_uow_runs(root, limit=args.limit)
    rows_raw: list[dict[str, Any]] = []
    for run in runs:
        detail_obj = run.get("detail")
        if not isinstance(detail_obj, dict):
            detail_obj = _detail(run)
        ts = run.get("created_at") or detail_obj.get("final_accepted_at")
        ts_s = ts if isinstance(ts, str) else None
        if not in_window(ts_s, since, until):
            continue
        rows_raw.append(classify_row(detail_obj, run))

    # stable order: oldest first
    rows_raw.sort(key=lambda r: str(r.get("created_at") or ""))

    metrics = compute_metrics(rows_raw)
    shadow = load_shadow_runs(root, limit=args.limit)
    shadow_obs = correlate_shadow(rows_raw, shadow)

    timestamps = [str(r.get("created_at")) for r in rows_raw if r.get("created_at")]
    date_range = {
        "first": min(timestamps) if timestamps else None,
        "last": max(timestamps) if timestamps else None,
    }

    payload = {
        "eval": "v3",
        "generated_at": _utcnow(),
        "frozen_sut_sha": baseline.get("frozen_sut_sha"),
        "root": str(root),
        "since": args.since,
        "until": args.until,
        "date_range": date_range,
        "real_request_count": metrics["total"],
        "synthetic_count": 0,
        "metrics": metrics,
        "rows": rows_raw,
        "jev_shadow_false_resolve_observations": shadow_obs,
        "baseline": baseline,
    }

    out_dir = ROOT / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "transmission_eval_v3_results.json"
    md_path = out_dir / "transmission_eval_v3_report.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = render_report(
        baseline=baseline,
        root=str(root),
        metrics=metrics,
        rows=rows_raw,
        shadow_obs=shadow_obs,
        since=args.since,
        until=args.until,
    )
    md_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
