#!/usr/bin/env python3
"""Run frozen transmission counter evaluation (20 queries).

Usage:
  PYTHONPATH=src:backend python experiments/run_transmission_eval_v1.py

Optional:
  JEV_DECISION_ENABLED=1  — run pass B with JEV gate (requires TYPESAFE_API_KEY)

Writes:
  experiments/transmission_eval_v1_results.json
  experiments/transmission_eval_v1_report.md

Does not modify resolver, decision policy, or production UI.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "backend"))

from parrts.dms.service import DmsService
from parrts.transmission.decision import apply_human_feedback, find_unit_of_work_run
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry

from transmission_eval_set_v1 import EVAL_CASES  # type: ignore  # noqa: E402


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_pass(label: str, *, jev_enabled: bool) -> dict:
    prev_jev = os.environ.get("JEV_DECISION_ENABLED")
    prev_shadow = os.environ.get("JEV_SHADOW_ENABLED")
    try:
        if jev_enabled:
            os.environ["JEV_DECISION_ENABLED"] = "1"
        else:
            os.environ.pop("JEV_DECISION_ENABLED", None)
        # keep shadow off for clean decision-source attribution
        os.environ.pop("JEV_SHADOW_ENABLED", None)

        rows: list[dict] = []
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            dms = DmsService(root)
            dms.ensure_schema()
            load_demo_seed(dms)

            for case in EVAL_CASES:
                ans = answer_transmission_inquiry(case["query"], dms)
                expected = case.get("expected_sku")
                system_outcome = ans.outcome
                system_sku = ans.sku
                rid = ans.request_id

                # Human evaluation protocol (frozen ground truth)
                human_verdict: str
                human_override: bool | None
                final_sku: str | None
                feedback_action: str | None = None
                feedback_ok: bool | None = None
                notes = case.get("notes") or ""

                if system_outcome == "RESOLVED" and system_sku:
                    if expected and system_sku == expected:
                        human_verdict = "accept"
                        human_override = False
                        final_sku = system_sku
                        fb = apply_human_feedback(
                            root, rid, action="accept", actor="eval"
                        )
                        feedback_ok = bool(fb.get("ok"))
                        feedback_action = "accept"
                    elif expected and system_sku != expected:
                        human_verdict = "correct"
                        human_override = True
                        final_sku = expected
                        fb = apply_human_feedback(
                            root,
                            rid,
                            action="correct",
                            final_sku=expected,
                            note="eval correction",
                            actor="eval",
                        )
                        feedback_ok = bool(fb.get("ok"))
                        feedback_action = "correct"
                    else:
                        # RESOLVED but ground truth says no single correct SKU
                        human_verdict = "false_resolution"
                        human_override = True
                        final_sku = None
                        # still mark override by resolving to a sentinel note-only path:
                        # use correct with a placeholder only if we must persist — skip persist
                        feedback_action = None
                        feedback_ok = None
                        notes = (notes + " | false RESOLVED with no expected SKU").strip(" |")
                else:
                    # NEEDS_HUMAN
                    if expected:
                        human_verdict = "manual_resolve"
                        human_override = True
                        final_sku = expected
                        fb = apply_human_feedback(
                            root,
                            rid,
                            action="resolve",
                            final_sku=expected,
                            note="eval manual resolve",
                            actor="eval",
                        )
                        feedback_ok = bool(fb.get("ok"))
                        feedback_action = "resolve"
                    else:
                        human_verdict = "leave_needs_human"
                        human_override = None
                        final_sku = None
                        feedback_action = None
                        feedback_ok = None

                ledger = None
                if rid and feedback_action:
                    run = find_unit_of_work_run(root, rid)
                    if run:
                        ledger = run.get("detail")

                rows.append(
                    {
                        "id": case["id"],
                        "query": case["query"],
                        "expected_sku": expected,
                        "system_outcome": system_outcome,
                        "system_status": ans.status,
                        "system_sku": system_sku,
                        "confidence": ans.confidence,
                        "candidate_match_quality": ans.candidate_match_quality,
                        "evidence_sufficiency": ans.evidence_sufficiency,
                        "decision_source": ans.decision_source,
                        "recommended_action": ans.recommended_action,
                        "ambiguity_reason": ans.ambiguity_reason,
                        "intent": ans.intent,
                        "request_id": rid,
                        "human_verdict": human_verdict,
                        "human_override": human_override,
                        "final_accepted_sku": final_sku
                        if human_verdict != "false_resolution"
                        else (ledger or {}).get("final_accepted_sku")
                        if ledger
                        else final_sku,
                        "feedback_action": feedback_action,
                        "feedback_ok": feedback_ok,
                        "notes": notes,
                        "ledger_system_sku": (ledger or {}).get("system_sku"),
                        "ledger_final_sku": (ledger or {}).get("final_accepted_sku"),
                        "ledger_human_override": (ledger or {}).get("human_override"),
                        "jev_consulted": bool(
                            (ans.decision or {}).get("decision", {}).get("jev_consulted")
                            if False
                            else (ans.decision or {}).get("decision", {})
                            and False
                        ),
                    }
                )
                # fix jev_consulted from decision blob
                dec = ans.decision or {}
                dsrc = dec.get("decision") if isinstance(dec.get("decision"), dict) else dec
                if isinstance(dsrc, dict):
                    rows[-1]["jev_consulted"] = bool(dsrc.get("jev_consulted"))
                    rows[-1]["jev_needs_human"] = dsrc.get("jev_needs_human")
                    rows[-1]["jev_label"] = dsrc.get("jev_label")

        metrics = compute_metrics(rows)
        return {
            "pass": label,
            "jev_enabled": jev_enabled,
            "rows": rows,
            "metrics": metrics,
        }
    finally:
        if prev_jev is None:
            os.environ.pop("JEV_DECISION_ENABLED", None)
        else:
            os.environ["JEV_DECISION_ENABLED"] = prev_jev
        if prev_shadow is None:
            os.environ.pop("JEV_SHADOW_ENABLED", None)
        else:
            os.environ["JEV_SHADOW_ENABLED"] = prev_shadow


def compute_metrics(rows: list[dict]) -> dict:
    n = len(rows)
    resolved = [r for r in rows if r["system_outcome"] == "RESOLVED"]
    needs = [r for r in rows if r["system_outcome"] == "NEEDS_HUMAN"]

    accepted_resolved = [
        r
        for r in resolved
        if r["human_verdict"] == "accept"
        and r.get("human_override") is False
    ]
    false_resolutions = [
        r
        for r in resolved
        if r["human_verdict"] in ("correct", "false_resolution")
        or (
            r.get("expected_sku")
            and r.get("system_sku")
            and r["system_sku"] != r["expected_sku"]
        )
    ]
    # de-dupe false resolution by id
    fr_ids = {r["id"] for r in false_resolutions}
    false_resolutions = [r for r in resolved if r["id"] in fr_ids]

    overrides = [r for r in rows if r.get("human_override") is True]
    autonomous = [
        r
        for r in rows
        if r["system_outcome"] == "RESOLVED"
        and r["human_verdict"] == "accept"
        and r.get("human_override") is False
    ]

    resolved_precision = (
        len(accepted_resolved) / len(resolved) if resolved else None
    )

    jev_escalations = [
        r
        for r in rows
        if r.get("jev_consulted")
        and r.get("jev_needs_human")
        and r.get("decision_source") == "deterministic_policy+jev"
    ]

    return {
        "total": n,
        "resolved_count": len(resolved),
        "needs_human_count": len(needs),
        "resolved_precision": resolved_precision,
        "human_escalation_rate": len(needs) / n if n else 0,
        "override_rate": len(overrides) / n if n else 0,
        "false_resolution_count": len(false_resolutions),
        "false_resolution_ids": [r["id"] for r in false_resolutions],
        "autonomous_accepted_coverage": len(autonomous) / n if n else 0,
        "autonomous_accepted_count": len(autonomous),
        "jev_escalation_count": len(jev_escalations),
        "jev_escalation_ids": [r["id"] for r in jev_escalations],
    }


def failure_groups(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {
        "false_resolution": [],
        "missed_resolution": [],  # NEEDS_HUMAN but expected_sku exists
        "correct_escalation": [],  # NEEDS_HUMAN and expected None
        "accepted_ok": [],
        "manual_resolve_after_escalation": [],
    }
    for r in rows:
        if r["system_outcome"] == "RESOLVED":
            if r["human_verdict"] == "accept":
                groups["accepted_ok"].append(r)
            else:
                groups["false_resolution"].append(r)
        else:
            if r.get("expected_sku"):
                groups["missed_resolution"].append(r)
                if r["human_verdict"] == "manual_resolve":
                    groups["manual_resolve_after_escalation"].append(r)
            else:
                groups["correct_escalation"].append(r)
    return groups


def render_report(pass_a: dict, pass_b: dict | None, baseline: str) -> str:
    lines: list[str] = []
    lines.append("# Transmission Counter Evaluation v1")
    lines.append("")
    lines.append(f"- Baseline commit: `{baseline}`")
    lines.append(f"- Generated: {_utcnow()}")
    lines.append(f"- Cases: {len(EVAL_CASES)}")
    lines.append("- System frozen: no resolver/policy changes during run")
    lines.append("")
    lines.append("## Pass A — deterministic policy only")
    lines.append("")
    ma = pass_a["metrics"]
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total requests | {ma['total']} |")
    lines.append(f"| RESOLVED | {ma['resolved_count']} |")
    lines.append(f"| NEEDS_HUMAN | {ma['needs_human_count']} |")
    lines.append(
        f"| Resolved precision | {ma['resolved_precision']:.3f} |"
        if ma["resolved_precision"] is not None
        else "| Resolved precision | n/a |"
    )
    lines.append(f"| Human escalation rate | {ma['human_escalation_rate']:.3f} |")
    lines.append(f"| Override rate | {ma['override_rate']:.3f} |")
    lines.append(f"| False-resolution count | {ma['false_resolution_count']} |")
    lines.append(
        f"| Autonomous accepted coverage | {ma['autonomous_accepted_coverage']:.3f} |"
    )
    lines.append("")

    lines.append("## Per-query results (Pass A)")
    lines.append("")
    lines.append(
        "| ID | Query | System | SKU | Conf | Human | Final SKU | Notes |"
    )
    lines.append("|----|-------|--------|-----|------|-------|-----------|-------|")
    for r in pass_a["rows"]:
        q = r["query"].replace("|", "/")
        lines.append(
            f"| {r['id']} | {q} | {r['system_outcome']}/{r['system_status']} | "
            f"{r['system_sku'] or '—'} | {r['confidence']} | {r['human_verdict']} | "
            f"{r['final_accepted_sku'] or '—'} | {(r['notes'] or '')[:60]} |"
        )
    lines.append("")

    groups = failure_groups(pass_a["rows"])
    lines.append("## Failure groups (Pass A)")
    lines.append("")
    for name, items in groups.items():
        lines.append(f"### {name} ({len(items)})")
        if not items:
            lines.append("- none")
        for r in items:
            lines.append(
                f"- **{r['id']}**: `{r['query']}` → system={r['system_outcome']} "
                f"sku={r['system_sku']} expected={r['expected_sku']} "
                f"verdict={r['human_verdict']}"
            )
        lines.append("")

    lines.append("## Pass B — deterministic + JEV gate")
    lines.append("")
    if pass_b is None:
        lines.append(
            "Not run (set `JEV_DECISION_ENABLED=1` and `TYPESAFE_API_KEY` to enable)."
        )
    else:
        mb = pass_b["metrics"]
        lines.append(f"| Metric | Pass A | Pass B |")
        lines.append(f"|--------|--------|--------|")
        lines.append(
            f"| Resolved precision | {ma['resolved_precision']} | {mb['resolved_precision']} |"
        )
        lines.append(
            f"| Escalation rate | {ma['human_escalation_rate']:.3f} | {mb['human_escalation_rate']:.3f} |"
        )
        lines.append(
            f"| False resolutions | {ma['false_resolution_count']} | {mb['false_resolution_count']} |"
        )
        lines.append(
            f"| Autonomous coverage | {ma['autonomous_accepted_coverage']:.3f} | {mb['autonomous_accepted_coverage']:.3f} |"
        )
        lines.append(
            f"| JEV escalations | {ma['jev_escalation_count']} | {mb['jev_escalation_count']} |"
        )
        lines.append("")
        # Compare row-level outcome flips
        flips = []
        by_id_b = {r["id"]: r for r in pass_b["rows"]}
        for r in pass_a["rows"]:
            b = by_id_b.get(r["id"])
            if not b:
                continue
            if r["system_outcome"] != b["system_outcome"] or r["system_sku"] != b["system_sku"]:
                flips.append((r, b))
        lines.append(f"Outcome/SKU flips A→B: {len(flips)}")
        for a, b in flips:
            lines.append(
                f"- {a['id']}: {a['system_outcome']}/{a['system_sku']} → "
                f"{b['system_outcome']}/{b['system_sku']} "
                f"(jev_needs_human={b.get('jev_needs_human')})"
            )
    lines.append("")

    lines.append("## Recommendations (do not implement yet)")
    lines.append("")
    fr = groups["false_resolution"]
    missed = groups["missed_resolution"]
    if fr:
        lines.append(
            "1. **Highest priority — false resolutions:** tighten decision policy or "
            "resolver when vehicle/family tokens conflict (see E08/E09-class cases)."
        )
    if missed:
        lines.append(
            "2. **Missed resolutions:** expand abbreviation/misspelling tokens only "
            f"for observed misses: {', '.join(r['id'] for r in missed)}."
        )
    lines.append(
        "3. Keep JEV opt-in until Pass B shows fewer false resolutions without "
        "large unnecessary escalation."
    )
    lines.append(
        "4. Do not generate rules from this set automatically; review failures manually."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    baseline = "39797b6f9366de9b2fecd86013c895238e9deccf"
    out_dir = ROOT / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    pass_a = run_pass("A_deterministic", jev_enabled=False)

    pass_b = None
    jev_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    want_b = os.environ.get("JEV_DECISION_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if want_b and jev_key:
        pass_b = run_pass("B_deterministic_plus_jev", jev_enabled=True)
    elif want_b and not jev_key:
        pass_b = {
            "pass": "B_skipped",
            "jev_enabled": True,
            "error": "TYPESAFE_API_KEY missing",
            "rows": [],
            "metrics": {},
        }

    payload = {
        "baseline_commit": baseline,
        "generated_at": _utcnow(),
        "cases": EVAL_CASES,
        "pass_a": pass_a,
        "pass_b": pass_b,
    }
    json_path = out_dir / "transmission_eval_v1_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report = render_report(
        pass_a,
        pass_b if pass_b and pass_b.get("rows") else None,
        baseline,
    )
    md_path = out_dir / "transmission_eval_v1_report.md"
    md_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
