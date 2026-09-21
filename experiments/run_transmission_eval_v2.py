#!/usr/bin/env python3
"""Run frozen Transmission Counter Evaluation v2 (unseen generalization).

Does not modify production code. Does not modify the case file after freeze.

  PYTHONPATH=src:backend:experiments python experiments/run_transmission_eval_v2.py

Pass B (live JEV):
  JEV_DECISION_ENABLED=1 TYPESAFE_API_KEY=…  (same command)
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from parrts.dms.service import DmsService
from parrts.transmission.decision import apply_human_feedback, find_unit_of_work_run
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry
from transmission_eval_set_v2 import EVAL_V2_CASES


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _verdict(system_outcome: str, system_sku: str | None, expected_outcome: str, expected_sku: str | None) -> str:
    """Classify system result vs frozen ground truth."""
    if expected_outcome == "RESOLVED" and expected_sku:
        if system_outcome == "RESOLVED" and system_sku == expected_sku:
            return "accept"
        if system_outcome == "RESOLVED" and system_sku != expected_sku:
            return "false_resolution"
        return "missed_resolution"  # NEEDS_HUMAN but expected resolve
    # expected NEEDS_HUMAN
    if system_outcome == "NEEDS_HUMAN":
        return "correct_escalation"
    # system RESOLVED but expected NEEDS_HUMAN
    return "false_resolution"


def run_pass(label: str, *, jev_enabled: bool) -> dict:
    prev_jev = os.environ.get("JEV_DECISION_ENABLED")
    prev_shadow = os.environ.get("JEV_SHADOW_ENABLED")
    try:
        if jev_enabled:
            os.environ["JEV_DECISION_ENABLED"] = "1"
        else:
            os.environ.pop("JEV_DECISION_ENABLED", None)
        os.environ.pop("JEV_SHADOW_ENABLED", None)

        rows: list[dict] = []
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            dms = DmsService(root)
            dms.ensure_schema()
            load_demo_seed(dms)

            for case in EVAL_V2_CASES:
                ans = answer_transmission_inquiry(case["query"], dms)
                expected_outcome = case["expected_outcome"]
                expected_sku = case.get("expected_sku")
                system_outcome = ans.outcome or (
                    "RESOLVED" if ans.status == "resolved" else "NEEDS_HUMAN"
                )
                system_sku = ans.sku
                rid = ans.request_id
                verdict = _verdict(
                    system_outcome, system_sku, expected_outcome, expected_sku
                )

                human_override = None
                final_sku = None
                feedback_action = None
                feedback_ok = None

                if verdict == "accept" and rid:
                    fb = apply_human_feedback(root, rid, action="accept", actor="eval_v2")
                    feedback_ok = bool(fb.get("ok"))
                    feedback_action = "accept"
                    human_override = False
                    final_sku = system_sku
                elif verdict == "false_resolution" and system_outcome == "RESOLVED" and expected_sku and rid:
                    fb = apply_human_feedback(
                        root,
                        rid,
                        action="correct",
                        final_sku=expected_sku,
                        note="eval_v2 correction",
                        actor="eval_v2",
                    )
                    feedback_ok = bool(fb.get("ok"))
                    feedback_action = "correct"
                    human_override = True
                    final_sku = expected_sku
                elif verdict == "missed_resolution" and expected_sku and rid:
                    fb = apply_human_feedback(
                        root,
                        rid,
                        action="resolve",
                        final_sku=expected_sku,
                        note="eval_v2 manual resolve",
                        actor="eval_v2",
                    )
                    feedback_ok = bool(fb.get("ok"))
                    feedback_action = "resolve"
                    human_override = True
                    final_sku = expected_sku
                elif verdict == "correct_escalation":
                    human_override = None
                    final_sku = None
                elif verdict == "false_resolution" and expected_outcome == "NEEDS_HUMAN":
                    # system resolved when should escalate — record without inventing SKU
                    human_override = True
                    final_sku = None
                    feedback_action = None

                dec = ans.decision or {}
                inner = dec.get("decision") if isinstance(dec.get("decision"), dict) else dec
                if not isinstance(inner, dict):
                    inner = {}

                rows.append(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "source_kind": case.get("source_kind", "synthetic"),
                        "query": case["query"],
                        "expected_outcome": expected_outcome,
                        "expected_sku": expected_sku,
                        "expected_reason": case.get("expected_reason"),
                        "truth_source": case.get("truth_source"),
                        "system_outcome": system_outcome,
                        "system_status": ans.status,
                        "system_sku": system_sku,
                        "confidence": ans.confidence,
                        "candidate_match_quality": ans.candidate_match_quality,
                        "evidence_sufficiency": ans.evidence_sufficiency,
                        "decision_source": ans.decision_source or inner.get("decision_source"),
                        "recommended_action": ans.recommended_action,
                        "ambiguity_reason": ans.ambiguity_reason,
                        "request_id": rid,
                        "verdict": verdict,
                        "human_override": human_override,
                        "final_accepted_sku": final_sku,
                        "feedback_action": feedback_action,
                        "feedback_ok": feedback_ok,
                        "jev_consulted": bool(inner.get("jev_consulted")),
                        "jev_needs_human": inner.get("jev_needs_human"),
                        "jev_label": inner.get("jev_label"),
                        "jev_choice_confidence": inner.get("jev_choice_confidence"),
                    }
                )

        return {
            "pass": label,
            "jev_enabled": jev_enabled,
            "rows": rows,
            "metrics": compute_metrics(rows),
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
    accepted = [r for r in resolved if r["verdict"] == "accept"]
    false_res = [r for r in rows if r["verdict"] == "false_resolution"]
    missed = [r for r in rows if r["verdict"] == "missed_resolution"]
    correct_esc = [r for r in rows if r["verdict"] == "correct_escalation"]
    # unnecessary escalation = missed_resolution (expected RESOLVED, got NEEDS_HUMAN)
    overrides = [r for r in rows if r.get("human_override") is True]
    autonomous = accepted

    # JEV escalations: consulted and flipped RESOLVED path via jev needs_human
    jev_esc = [
        r
        for r in rows
        if r.get("jev_consulted")
        and r.get("decision_source") == "deterministic_policy+jev"
        and r.get("jev_needs_human") is True
        and r["system_outcome"] == "NEEDS_HUMAN"
    ]

    return {
        "total": n,
        "resolved_count": len(resolved),
        "needs_human_count": len(needs),
        "resolved_precision": (len(accepted) / len(resolved)) if resolved else None,
        "false_resolution_count": len(false_res),
        "false_resolution_ids": [r["id"] for r in false_res],
        "missed_resolution_count": len(missed),
        "missed_resolution_ids": [r["id"] for r in missed],
        "correct_escalation_count": len(correct_esc),
        "false_escalation_count": len(missed),  # same as missed when expected RESOLVED
        "human_escalation_rate": len(needs) / n if n else 0,
        "override_rate": len(overrides) / n if n else 0,
        "autonomous_accepted_coverage": len(autonomous) / n if n else 0,
        "autonomous_accepted_count": len(autonomous),
        "jev_escalation_count": len(jev_esc),
        "jev_escalation_ids": [r["id"] for r in jev_esc],
        "category_counts": dict(Counter(r["category"] for r in rows)),
        "source_counts": dict(Counter(r["source_kind"] for r in rows)),
        "verdict_counts": dict(Counter(r["verdict"] for r in rows)),
    }


def render_report(pass_a: dict, pass_b: dict | None, freeze_sha: str, sut: str) -> str:
    lines: list[str] = []
    lines.append("# Transmission Counter Evaluation v2")
    lines.append("")
    lines.append(f"- Freeze commit (cases): `{freeze_sha}`")
    lines.append(f"- SUT: `{sut}`")
    lines.append(f"- Generated: {_utcnow()}")
    lines.append(f"- Cases: {len(EVAL_V2_CASES)}")
    real = sum(1 for c in EVAL_V2_CASES if c.get("source_kind") == "real")
    synth = len(EVAL_V2_CASES) - real
    lines.append(f"- Real JP requests: {real}")
    lines.append(f"- Synthetic blind: {synth}")
    lines.append("")
    ma = pass_a["metrics"]
    lines.append("## Category distribution")
    lines.append("")
    for k, v in sorted((ma.get("category_counts") or {}).items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Pass A — deterministic only")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total | {ma['total']} |")
    lines.append(f"| RESOLVED | {ma['resolved_count']} |")
    lines.append(f"| NEEDS_HUMAN | {ma['needs_human_count']} |")
    rp = ma["resolved_precision"]
    lines.append(f"| Resolved precision | {rp if rp is None else f'{rp:.3f}'} |")
    lines.append(f"| False-resolution count | {ma['false_resolution_count']} |")
    lines.append(f"| Missed-resolution count | {ma['missed_resolution_count']} |")
    lines.append(f"| Correct escalations | {ma['correct_escalation_count']} |")
    lines.append(f"| Escalation rate | {ma['human_escalation_rate']:.3f} |")
    lines.append(f"| Override rate | {ma['override_rate']:.3f} |")
    lines.append(f"| Autonomous accepted coverage | {ma['autonomous_accepted_coverage']:.3f} |")
    lines.append("")
    lines.append("### False RESOLVED")
    if not ma["false_resolution_ids"]:
        lines.append("- none")
    else:
        by_id = {r["id"]: r for r in pass_a["rows"]}
        for i in ma["false_resolution_ids"]:
            r = by_id[i]
            lines.append(
                f"- **{i}** [{r['category']}] `{r['query']}` → "
                f"system={r['system_outcome']}/{r['system_sku']} "
                f"expected={r['expected_outcome']}/{r['expected_sku']}"
            )
    lines.append("")
    lines.append("### Missed resolutions")
    if not ma["missed_resolution_ids"]:
        lines.append("- none")
    else:
        by_id = {r["id"]: r for r in pass_a["rows"]}
        for i in ma["missed_resolution_ids"]:
            r = by_id[i]
            lines.append(
                f"- **{i}** [{r['category']}] `{r['query']}` → "
                f"system={r['system_outcome']} expected_sku={r['expected_sku']}"
            )
    lines.append("")
    lines.append("## Pass B — deterministic + live JEV")
    lines.append("")
    if not pass_b or not pass_b.get("rows"):
        lines.append("Not run or empty.")
    else:
        mb = pass_b["metrics"]
        lines.append("| Metric | Pass A | Pass B |")
        lines.append("|--------|--------|--------|")
        lines.append(f"| Resolved precision | {ma['resolved_precision']} | {mb['resolved_precision']} |")
        lines.append(f"| False resolutions | {ma['false_resolution_count']} | {mb['false_resolution_count']} |")
        lines.append(f"| Missed resolutions | {ma['missed_resolution_count']} | {mb['missed_resolution_count']} |")
        lines.append(f"| Escalation rate | {ma['human_escalation_rate']:.3f} | {mb['human_escalation_rate']:.3f} |")
        lines.append(f"| Autonomous coverage | {ma['autonomous_accepted_coverage']:.3f} | {mb['autonomous_accepted_coverage']:.3f} |")
        lines.append(f"| JEV escalations | — | {mb['jev_escalation_count']} |")
        lines.append("")
        pa = {r["id"]: r for r in pass_a["rows"]}
        flips = []
        for r in pass_b["rows"]:
            a = pa[r["id"]]
            if (a["system_outcome"], a.get("system_sku")) != (
                r["system_outcome"],
                r.get("system_sku"),
            ):
                flips.append((a, r))
        lines.append(f"### A → B flips ({len(flips)})")
        if not flips:
            lines.append("- none")
        for a, b in flips:
            lines.append(
                f"- **{a['id']}**: {a['system_outcome']}/{a.get('system_sku')} → "
                f"{b['system_outcome']}/{b.get('system_sku')} "
                f"(jev_nh={b.get('jev_needs_human')}, label={b.get('jev_label')})"
            )
        lines.append("")
        consulted = sum(1 for r in pass_b["rows"] if r.get("jev_consulted"))
        lines.append(f"JEV consulted: {consulted}/{len(pass_b['rows'])}")
        labels = Counter(r.get("jev_label") for r in pass_b["rows"] if r.get("jev_consulted"))
        lines.append(f"JEV labels: {dict(labels)}")
        lines.append(f"JEV escalation IDs: {mb.get('jev_escalation_ids')}")
    lines.append("")
    lines.append("## Comparison to Eval v1 (frozen)")
    lines.append("")
    lines.append("| Metric | Eval v1 A | Eval v2 A |")
    lines.append("|--------|-----------|-----------|")
    lines.append("| Cases | 20 | 90 |")
    lines.append("| Resolved precision | 1.000 | " + f"{ma['resolved_precision']}" + " |")
    lines.append("| False resolutions | 0 | " + str(ma["false_resolution_count"]) + " |")
    lines.append("| Autonomous coverage | 0.700 | " + f"{ma['autonomous_accepted_coverage']:.3f}" + " |")
    lines.append("| Escalation rate | 0.300 | " + f"{ma['human_escalation_rate']:.3f}" + " |")
    lines.append("")
    lines.append("## Recommendations (do not implement yet)")
    lines.append("")
    lines.append("See final agent report — ranked by severity from this measurement only.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    sut = "8fd2e28decb8154f61fde49fdc4df37c2ba9096b"
    freeze = os.environ.get("EVAL_V2_FREEZE_SHA", "PENDING_FREEZE")
    out_dir = ROOT / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    pass_a = run_pass("A_deterministic", jev_enabled=False)

    pass_b = None
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    want_b = os.environ.get("RUN_PASS_B", "1").strip() not in ("0", "false", "no")
    if want_b and key:
        pass_b = run_pass("B_deterministic_plus_jev", jev_enabled=True)
    elif want_b and not key:
        pass_b = {
            "pass": "B_skipped",
            "jev_enabled": True,
            "error": "TYPESAFE_API_KEY missing",
            "rows": [],
            "metrics": {},
        }

    payload = {
        "freeze_sha": freeze,
        "sut": sut,
        "generated_at": _utcnow(),
        "case_count": len(EVAL_V2_CASES),
        "pass_a": pass_a,
        "pass_b": pass_b,
    }
    json_path = out_dir / "transmission_eval_v2_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = render_report(
        pass_a,
        pass_b if pass_b and pass_b.get("rows") else None,
        freeze,
        sut,
    )
    md_path = out_dir / "transmission_eval_v2_report.md"
    md_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
