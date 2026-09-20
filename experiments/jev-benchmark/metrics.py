"""Benchmark metrics (classification + needs_human + latency).

Pure functions — no I/O. Produce everything the report needs from a list of
per-row results: accuracy, per-class P/R/F1, confusion matrix, needs_human
accuracy, and latency percentiles.
"""
from __future__ import annotations

import statistics
from collections import Counter

__all__ = [
    "accuracy",
    "per_class_metrics",
    "confusion_matrix",
    "needs_human_accuracy",
    "latency_stats",
]


def accuracy(preds: list[str], golds: list[str]) -> float:
    if not golds:
        return 0.0
    correct = sum(1 for p, g in zip(preds, golds) if p == g)
    return correct / len(golds)


def per_class_metrics(preds: list[str], golds: list[str], classes: tuple[str, ...]) -> dict:
    """Precision / recall / F1 per class (macro over provided classes)."""
    out: dict[str, dict] = {}
    for cls in classes:
        tp = sum(1 for p, g in zip(preds, golds) if p == cls and g == cls)
        fp = sum(1 for p, g in zip(preds, golds) if p == cls and g != cls)
        fn = sum(1 for p, g in zip(preds, golds) if p != cls and g == cls)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        out[cls] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
    return out


def confusion_matrix(preds: list[str], golds: list[str], classes: tuple[str, ...]) -> dict:
    """{gold: {pred: count}}."""
    m = {g: {p: 0 for p in classes} for g in classes}
    for p, g in zip(preds, golds):
        m[g][p] = m[g].get(p, 0) + 1
    return m


def needs_human_accuracy(pred_needs_human: list[bool], gold_needs_human: list[bool]) -> dict:
    """Accuracy + confusion for the separate adjudication flag."""
    tp = sum(1 for p, g in zip(pred_needs_human, gold_needs_human) if p and g)
    tn = sum(1 for p, g in zip(pred_needs_human, gold_needs_human) if not p and not g)
    fp = sum(1 for p, g in zip(pred_needs_human, gold_needs_human) if p and not g)
    fn = sum(1 for p, g in zip(pred_needs_human, gold_needs_human) if not p and g)
    total = len(gold_needs_human)
    acc = (tp + tn) / total if total else 0.0
    return {
        "accuracy": round(acc, 4),
        "needs_human_confusion": {
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "precision_need": round(tp / (tp + fp), 4) if (tp + fp) else 0.0,
            "recall_need": round(tp / (tp + fn), 4) if (tp + fn) else 0.0,
        },
    }


def latency_stats(latencies: list[float]) -> dict:
    if not latencies:
        return {"mean_s": 0.0, "p50_s": 0.0, "p95_s": 0.0, "min_s": 0.0, "max_s": 0.0}
    s = sorted(latencies)
    def pct(p: float) -> float:
        if not s:
            return 0.0
        k = (len(s) - 1) * p
        f = int(k)
        base = s[f]
        return base if f + 1 >= len(s) else base + (s[f + 1] - base) * (k - f)
    return {
        "mean_s": round(statistics.mean(s), 6),
        "median_s": round(statistics.median(s), 6),
        "p50_s": round(pct(0.50), 6),
        "p95_s": round(pct(0.95), 6),
        "min_s": round(s[0], 6),
        "max_s": round(s[-1], 6),
        "count": len(s),
    }