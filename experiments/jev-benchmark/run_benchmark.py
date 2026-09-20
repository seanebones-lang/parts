"""JEV benchmark runner.

Usage (from repo root):
    PYTHONPATH=src python experiments/jev-benchmark/run_benchmark.py
        --approach rule_based          # deterministic only (this iteration)
    PYTHONPATH=backend:src python experiments/jev-benchmark/run_benchmark.py \
        --approach rule_based --approach llm_existing --approach jev

Optional LLM adapter is self-gated: if credentials/backend deps are missing it
is skipped cleanly (never fails the run). JEV remains a stub and is skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import labels as BENCH_LABELS
import metrics as M

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Allow importing approach modules by name
sys.path.insert(0, str(HERE / "approaches"))


def load_corpus() -> list[dict]:
    p = HERE / "corpus" / "gold_labels.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"corpus not built: {p} (run corpus/build_corpus.py)")
    rows = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _pick_row(errors: list[str]) -> list[str]:
    return errors


def run_approach(name: str, corpus: list[dict], workers: int = 1) -> dict:
    """Run one approach over the corpus, return its report section.

    ``workers>1`` runs the per-row classification concurrently (used to dodge
    the NVIDIA free-tier rate throttle on long LLM batch runs). Deterministic
    rule-based runs always single-threaded (trivial latency)."""
    if name == "rule_based":
        from approaches import rule_based as impl
    elif name == "llm_existing":
        from approaches import llm_existing as impl
    elif name == "jev":
        from approaches import jev as impl
    else:
        raise ValueError(f"unknown approach: {name}")

    cfg = impl.config()

    # Optional/gated approaches: skip cleanly when unavailable or unimplemented.
    if cfg.get("implemented") is False:
        return {"approach": name, "status": "skipped", "reason": "not implemented (JEV stub)", "config": cfg}

    if cfg.get("available") is False and name == "llm_existing":
        return {"approach": name, "status": "skipped", "reason": cfg.get("reason", "unavailable"), "config": cfg}

    def _run_one(row: dict) -> dict:
        base = {
            "message_id": row.get("message_id", ""),
            "gold_label": row["label"],
            "gold_needs_human": bool(row.get("needs_human", False)),
        }
        try:
            r = impl.classify(
                subject=row.get("subject", ""),
                body=row.get("body", ""),
                sender_email=row.get("sender_email", ""),
            )
            return {
                **base,
                "pred_label": r.get("label", "general_question"),
                "pred_needs_human": bool(r.get("needs_human", False)),
                "latency_s": float(r.get("latency_s", 0.0)),
                "cost_usd": float(r.get("cost_usd", 0.0)),
                "confidence": float(r.get("confidence", 0.0)),
                "input_tokens": r.get("input_tokens"),
                "output_tokens": r.get("output_tokens"),
                "total_tokens": r.get("total_tokens"),
                "provider": r.get("provider"),
                "model": r.get("model"),
            }
        except Exception as exc:  # record failure, do NOT silently fall back
            return {
                **base,
                "pred_label": "ERROR",
                "pred_needs_human": True,
                "latency_s": 0.0,
                "cost_usd": 0.0,
                "confidence": 0.0,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "error": str(exc),
            }

    results = []
    api_failures = 0
    if workers > 1 and name == "llm_existing":
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(_run_one, corpus):
                if res.get("pred_label") == "ERROR":
                    api_failures += 1
                results.append(res)
    else:
        for row in corpus:
            res = _run_one(row)
            if res.get("pred_label") == "ERROR":
                api_failures += 1
            results.append(res)

    preds = [x["pred_label"] for x in results]
    golds = [x["gold_label"] for x in results]
    nh_pred = [x["pred_needs_human"] for x in results]
    nh_gold = [x["gold_needs_human"] for x in results]
    lats = [x["latency_s"] for x in results]
    costs = [x["cost_usd"] for x in results]

    report = {
        "approach": name,
        "status": "ok",
        "api_failures": api_failures,
        "config": cfg,
        "accuracy": round(M.accuracy(preds, golds), 4),
        "per_class": M.per_class_metrics(preds, golds, BENCH_LABELS.CLASSES),
        "confusion_matrix": M.confusion_matrix(preds, golds, BENCH_LABELS.CLASSES),
        "needs_human": M.needs_human_accuracy(nh_pred, nh_gold),
        "latency": M.latency_stats(lats),
        "cost": {"total_usd": round(sum(costs), 6), "per_query_mean": round(sum(costs) / len(costs), 6) if costs else 0.0},
        "per_row": results,
    }
    return report


def summarize_section(title: str, body: str) -> str:
    return f"\n===== {title} =====\n{body}\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="JEV classification benchmark runner")
    ap.add_argument(
        "--approach",
        action="append",
        default=["rule_based"],
        help="approach to run (rule_based|llm_existing|jev); repeatable",
    )
    ap.add_argument("--out", default="results/report.json", help="output path (relative to benchmark dir)")
    ap.add_argument(
        "--workers",
        type=int,
        default=1,
        help="concurrent worker threads for LLM batch classification (default 1)",
    )
    args = ap.parse_args()

    corpus = load_corpus()
    report = {
        "corpus": {
            "total": len(corpus),
            "per_class": dict(Counter(r["label"] for r in corpus)),
            "needs_human_true": sum(1 for r in corpus if r["needs_human"]),
            "needs_human_false": sum(1 for r in corpus if not r["needs_human"]),
            "gold_label_sources": dict(Counter(r.get("source", "?") for r in corpus)),
        },
        "approaches": {},
    }

    for name in args.approach:
        report["approaches"][name] = run_approach(name, corpus, workers=args.workers)

    out_path = HERE / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))

    # Human-readable print
    print(f"Corpus: {report['corpus']['total']} rows")
    print("  per-class:", report["corpus"]["per_class"])
    print("  needs_human true:", report["corpus"]["needs_human_true"], "false:", report["corpus"]["needs_human_false"])
    for name, sec in report["approaches"].items():
        print()
        print(f"--- {name}: {sec.get('status')} ---")
        if sec.get("status") != "ok":
            print("  reason:", sec.get("reason", ""))
            continue
        print(f"  accuracy: {sec['accuracy']:.4f}")
        print("  per-class P/R/F1:")
        for cls, m in sec["per_class"].items():
            print(f"    {cls:24s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} (n={m['support']})")
        print("  needs_human:", sec["needs_human"])
        print("  latency:", sec["latency"])
        print("  cost:", sec["cost"])
    print("\nFull JSON report written to:", out_path)


if __name__ == "__main__":
    main()