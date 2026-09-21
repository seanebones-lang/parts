#!/usr/bin/env python3
"""Run frozen Transmission Eval v2b against frozen SUT (deterministic only).

Does not modify production code or the case file.

  PYTHONPATH=src:backend:experiments \\
    python experiments/run_transmission_eval_v2b.py
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
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry

CASES_PATH = Path(__file__).resolve().parent / "transmission_eval_set_v2b.json"
META_PATH = Path(__file__).resolve().parent / "transmission_eval_v2b_meta.json"
FROZEN_SUT = "932af65d58201a3e2be50fa4ed9262f136ce3598"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _verdict(
    system_outcome: str,
    system_sku: str | None,
    expected_outcome: str,
    expected_sku: str | None,
) -> str:
    if expected_outcome == "RESOLVED" and expected_sku:
        if system_outcome == "RESOLVED" and system_sku == expected_sku:
            return "accept"
        if system_outcome == "RESOLVED" and system_sku != expected_sku:
            return "false_resolution"
        return "missed_resolution"
    if system_outcome == "NEEDS_HUMAN":
        return "correct_escalation"
    return "false_resolution"


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def run_deterministic(cases: list[dict]) -> dict:
    # Ensure JEV off
    os.environ.pop("JEV_DECISION_ENABLED", None)
    os.environ.pop("JEV_SHADOW_ENABLED", None)
    os.environ["JEV_DECISION_ENABLED"] = "0"

    rows: list[dict] = []
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dms = DmsService(root)
        dms.ensure_schema()
        load_demo_seed(dms)

        for case in cases:
            ans = answer_transmission_inquiry(case["query"], dms)
            system_outcome = ans.outcome or (
                "RESOLVED" if ans.status == "resolved" else "NEEDS_HUMAN"
            )
            system_sku = ans.sku
            expected_outcome = case["expected_outcome"]
            expected_sku = case.get("expected_sku")
            verdict = _verdict(
                system_outcome, system_sku, expected_outcome, expected_sku
            )
            rows.append(
                {
                    "id": case["id"],
                    "raw_query": case["query"],
                    "cohort": case.get("cohort"),
                    "category": case.get("category"),
                    "mutation_type": case.get("mutation_type"),
                    "adversarial_category": case.get("adversarial_category"),
                    "canonical_source": case.get("canonical_source"),
                    "expected_outcome": expected_outcome,
                    "expected_sku": expected_sku,
                    "expected_reason": case.get("expected_reason"),
                    "system_outcome": system_outcome,
                    "system_sku": system_sku,
                    "confidence": ans.confidence,
                    "candidate_match_quality": ans.candidate_match_quality,
                    "evidence_sufficiency": ans.evidence_sufficiency,
                    "ambiguity_reason": ans.ambiguity_reason,
                    "recommended_action": ans.recommended_action,
                    "decision_source": ans.decision_source,
                    "request_id": ans.request_id,
                    "verdict": verdict,
                }
            )
    return {"rows": rows, "metrics": compute_metrics(rows)}


def compute_metrics(rows: list[dict]) -> dict:
    n = len(rows)
    exp_res = [r for r in rows if r["expected_outcome"] == "RESOLVED"]
    exp_nh = [r for r in rows if r["expected_outcome"] == "NEEDS_HUMAN"]
    act_res = [r for r in rows if r["system_outcome"] == "RESOLVED"]
    act_nh = [r for r in rows if r["system_outcome"] == "NEEDS_HUMAN"]
    accepts = [r for r in rows if r["verdict"] == "accept"]
    false_res = [r for r in rows if r["verdict"] == "false_resolution"]
    missed = [r for r in rows if r["verdict"] == "missed_resolution"]
    correct_esc = [r for r in rows if r["verdict"] == "correct_escalation"]
    # unnecessary escalation = missed when expected RESOLVED
    return {
        "total": n,
        "expected_resolved_count": len(exp_res),
        "expected_needs_human_count": len(exp_nh),
        "actual_resolved_count": len(act_res),
        "actual_needs_human_count": len(act_nh),
        "resolved_precision": (len(accepts) / len(act_res)) if act_res else None,
        "false_resolution_count": len(false_res),
        "false_resolution_rate": (len(false_res) / n) if n else 0.0,
        "false_resolution_ids": [r["id"] for r in false_res],
        "autonomous_accepted_count": len(accepts),
        "autonomous_accepted_coverage": (len(accepts) / n) if n else 0.0,
        "escalation_rate": (len(act_nh) / n) if n else 0.0,
        "correct_escalation_count": len(correct_esc),
        "correct_escalation_rate": (len(correct_esc) / len(exp_nh)) if exp_nh else None,
        "unnecessary_escalation_count": len(missed),
        "missed_resolution_count": len(missed),
        "missed_resolution_ids": [r["id"] for r in missed],
        "override_equivalent_rate": (len(false_res) + len(missed)) / n if n else 0.0,
        "verdict_counts": dict(Counter(r["verdict"] for r in rows)),
        "cohort_verdicts": {
            cohort: dict(Counter(r["verdict"] for r in rows if r.get("cohort") == cohort))
            for cohort in sorted({r.get("cohort") for r in rows})
        },
    }


def render_internal(meta: dict, freeze_sha: str, sut: str, result: dict) -> str:
    m = result["metrics"]
    rows = result["rows"]
    lines = [
        "# Transmission Eval v2b — Synthetic Pressure Test (internal)",
        "",
        f"- Generated: `{_utcnow()}`",
        f"- Corpus freeze SHA: `{freeze_sha}`",
        f"- SUT: `{sut}`",
        f"- RNG seed: `{meta.get('rng_seed')}`",
        f"- Cases: **{m['total']}** (synthetic; not live JP traffic)",
        "",
        "## Metrics (deterministic only, JEV off)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Expected RESOLVED | {m['expected_resolved_count']} |",
        f"| Expected NEEDS_HUMAN | {m['expected_needs_human_count']} |",
        f"| Actual RESOLVED | {m['actual_resolved_count']} |",
        f"| Actual NEEDS_HUMAN | {m['actual_needs_human_count']} |",
        f"| Resolved precision | {m['resolved_precision']} |",
        f"| False-resolution count | {m['false_resolution_count']} |",
        f"| False-resolution rate | {m['false_resolution_rate']:.4f} |",
        f"| Autonomous accepted coverage | {m['autonomous_accepted_coverage']:.3f} |",
        f"| Escalation rate | {m['escalation_rate']:.3f} |",
        f"| Correct escalation count | {m['correct_escalation_count']} |",
        f"| Correct escalation rate (vs expected NH) | {m['correct_escalation_rate']} |",
        f"| Unnecessary escalation / missed-resolution | {m['missed_resolution_count']} |",
        f"| Override-equivalent rate | {m['override_equivalent_rate']:.3f} |",
        "",
        "## Verdict counts",
        "",
        f"```json\n{json.dumps(m['verdict_counts'], indent=2)}\n```",
        "",
        "## Cohort verdicts",
        "",
        f"```json\n{json.dumps(m['cohort_verdicts'], indent=2)}\n```",
        "",
        "## FALSE RESOLVED (complete list)",
        "",
    ]
    by_id = {r["id"]: r for r in rows}
    if not m["false_resolution_ids"]:
        lines.append("- none")
    else:
        for i in m["false_resolution_ids"]:
            r = by_id[i]
            lines.append(
                f"- **{i}** [{r.get('cohort')}/{r.get('category')}] "
                f"query=`{r['raw_query']}` "
                f"system={r['system_outcome']}/{r.get('system_sku')} "
                f"expected={r['expected_outcome']}/{r.get('expected_sku')} "
                f"amb=`{r.get('ambiguity_reason')}`"
            )
    lines.append("")
    lines.append("## Missed resolutions (sample up to 40)")
    lines.append("")
    missed = [by_id[i] for i in m["missed_resolution_ids"]]
    if not missed:
        lines.append("- none")
    else:
        for r in missed[:40]:
            lines.append(
                f"- **{r['id']}** [{r.get('mutation_type') or r.get('category')}] "
                f"`{r['raw_query']}` → {r['system_outcome']} "
                f"expected_sku={r.get('expected_sku')}"
            )
        if len(missed) > 40:
            lines.append(f"- … +{len(missed) - 40} more")
    lines.append("")
    lines.append("## Failure groups (post-hoc)")
    lines.append("")
    # group false + missed by category
    fail = [r for r in rows if r["verdict"] in ("false_resolution", "missed_resolution")]
    lines.append("```json")
    lines.append(
        json.dumps(
            {
                "by_verdict_category": dict(
                    Counter((r["verdict"], r.get("category")) for r in fail)
                ),
                "by_mutation": dict(
                    Counter(
                        r.get("mutation_type") or "n/a"
                        for r in fail
                        if r["verdict"] == "missed_resolution"
                    )
                ),
                "by_adversarial": dict(
                    Counter(
                        r.get("adversarial_category") or "n/a"
                        for r in fail
                        if r["verdict"] == "false_resolution"
                    )
                ),
            },
            indent=2,
            default=str,
        )
    )
    lines.append("```")
    lines.append("")
    lines.append("## Recommendations (do not implement in this task)")
    lines.append("")
    lines.append("See agent final report.")
    lines.append("")
    return "\n".join(lines)


def render_client(meta: dict, freeze_sha: str, sut: str, result: dict) -> str:
    m = result["metrics"]
    rows = result["rows"]
    accepts = [r for r in rows if r["verdict"] == "accept"]
    correct_esc = [r for r in rows if r["verdict"] == "correct_escalation"]
    false_res = [r for r in rows if r["verdict"] == "false_resolution"]
    lines = [
        "# JP Transmission — Synthetic Engineering Pressure Test (Eval v2b)",
        "",
        "> **Synthetic engineering pressure test — not yet a measurement of live JP Transmission counter traffic.**",
        ">",
        "> These results measure how a frozen parts-resolution engine behaves on a large, deliberately constructed set of shop-style and adversarial queries derived from pilot catalog data. They are **not** real-world accuracy on JP counter history.",
        "",
        f"- Cases: **{m['total']}** synthetic requests",
        f"- Generator seed: `{meta.get('rng_seed')}`",
        f"- Corpus freeze: `{freeze_sha}`",
        f"- Engine build under test: `{sut}`",
        f"- Source data: pilot transmission catalog ({meta.get('canonical_part_count')} hard-parts SKUs), identifiers, fitments, inventory phrasing",
        "",
        "## What was tested",
        "",
        "- Valid lookups (family + part, SKU, OEM/casting identifiers, vehicle + family when fitment exists)",
        "- Counter-language variation (case, urgency, plurals, known abbreviations like VB/pmp)",
        "- Deliberately bad inputs: multi-part requests, substitution language, vehicle/family conflicts, unsupported vehicle+family, unknown IDs, nonsense",
        "",
        "## Headline metrics",
        "",
        "| Metric | Result |",
        "|--------|--------|",
        f"| Resolved precision (of system RESOLVED) | **{(m['resolved_precision'] or 0)*100:.1f}%** |",
        f"| False-resolution rate (of all cases) | **{m['false_resolution_rate']*100:.2f}%** ({m['false_resolution_count']} cases) |",
        f"| Autonomous accepted coverage | **{m['autonomous_accepted_coverage']*100:.1f}%** |",
        f"| Escalation rate (NEEDS_HUMAN) | **{m['escalation_rate']*100:.1f}%** |",
        "",
        "## Representative successes",
        "",
    ]
    for r in accepts[:8]:
        lines.append(
            f"- `{r['raw_query']}` → **{r['system_sku']}**"
        )
    lines.append("")
    lines.append("## Representative safe refusals")
    lines.append("")
    for r in correct_esc[:8]:
        lines.append(
            f"- `{r['raw_query']}` → **NEEDS HUMAN REVIEW**"
            + (f" ({r.get('ambiguity_reason')})" if r.get("ambiguity_reason") else "")
        )
    lines.append("")
    lines.append("## Discovered false resolutions")
    lines.append("")
    if not false_res:
        lines.append("- None on this synthetic set.")
    else:
        lines.append(
            "The system returned a confident part where the test expected human review or a different part:"
        )
        for r in false_res[:25]:
            lines.append(
                f"- `{r['raw_query']}` → system `{r.get('system_sku')}` "
                f"(expected {r['expected_outcome']}/{r.get('expected_sku')})"
            )
        if len(false_res) > 25:
            lines.append(f"- … +{len(false_res) - 25} more (full list in internal report)")
    lines.append("")
    lines.append("## Important framing for JP")
    lines.append("")
    lines.append(
        "This pressure test increases confidence that the engine **refuses many unsafe patterns** "
        "and **resolves clean catalog-backed requests** at scale. "
        "**Live JP counter traffic (Eval v3)** remains the real-world measurement and is separate."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not CASES_PATH.is_file():
        print(f"Missing frozen cases: {CASES_PATH}", file=sys.stderr)
        return 2
    meta = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.is_file() else {}
    cases = load_cases()
    freeze_sha = os.environ.get("EVAL_V2B_FREEZE_SHA", "PENDING")
    sut = os.environ.get("EVAL_V2B_SUT", FROZEN_SUT)

    # JEV must stay out of primary score
    os.environ["JEV_DECISION_ENABLED"] = "0"
    result = run_deterministic(cases)

    payload = {
        "eval": "v2b",
        "generated_at": _utcnow(),
        "freeze_sha": freeze_sha,
        "sut": sut,
        "rng_seed": meta.get("rng_seed"),
        "case_count": len(cases),
        "jev": "off",
        "metrics": result["metrics"],
        "rows": result["rows"],
        "meta": meta,
        "disclaimer": "Synthetic engineering pressure test — not live JP counter traffic.",
    }
    out_json = ROOT / "experiments" / "transmission_eval_v2b_results.json"
    out_md = ROOT / "experiments" / "transmission_eval_v2b_report.md"
    out_client = ROOT / "experiments" / "transmission_eval_v2b_client_summary.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    internal = render_internal(meta, freeze_sha, sut, result)
    client = render_client(meta, freeze_sha, sut, result)
    out_md.write_text(internal, encoding="utf-8")
    out_client.write_text(client, encoding="utf-8")
    print(internal)
    print("\n--- client summary written ---")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_client}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
