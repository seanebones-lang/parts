"""Production-oriented hybrid classifier (Phase 4).

Conservative router:
1. High-recall risk/escalation gate first
2. Very narrow deterministic bypass (only subsets with empirically high precision)
3. Grok fallback for everything else

Grok confidence is not usable (always 1.0 in frozen adapter), so no confidence-based routing on Grok outputs.
"""
from __future__ import annotations

import time
from typing import Any

from labels import CLASSES

# Pre-declared frozen threshold for needs_human probability
NEEDS_HUMAN_THRESHOLD = 0.50


def _is_risky(subject: str, body: str, sender_email: str) -> bool:
    """High-recall risk gate. False positives acceptable."""
    text = f"{subject} {body}".lower()

    risk_signals = [
        "complaint", "unacceptable", "refund now", "lawsuit", "attorney",
        "bbb", "better business", "scam", "fraud", "dispute", "chargeback",
        "unsafe", "dangerous", "injury", "manager", "speak to a human",
        "speak to a person", "escalate", "threat", "legal action",
        "angry", "furious", "worst", "never again",
    ]
    for sig in risk_signals:
        if sig in text:
            return True

    # Explicit human request
    if any(p in text for p in ["speak to", "talk to", "human", "person", "manager"]):
        return True

    return False


def _narrow_deterministic_bypass(subject: str, body: str) -> tuple[str | None, float]:
    """
    Extremely conservative deterministic bypass.
    Only returns a label if precision is expected to be very high based on frozen analysis.
    Returns (label or None, confidence)
    """
    text = f"{subject} {body}".lower()

    # Narrow order_status bypass (tracking/shipment language, no risk signals)
    if any(w in text for w in ["tracking", "ups", "fedex", "shipped", "delivery eta", "in transit"]):
        if "order" in text or "shipment" in text:
            return "order_status", 0.85

    # Very narrow price_request bypass (pure price + part + vehicle, no fitment language)
    price_words = ["how much", "price", "cost", "quote"]
    part_words = ["brake", "pad", "rotor", "filter", "spark"]
    has_price = any(w in text for w in price_words)
    has_part = any(w in text for w in part_words)
    has_vehicle = any(y in text for y in ["civic", "camry", "f-150", "accord", "rav4"])

    if has_price and has_part and has_vehicle and "fit" not in text and "compatible" not in text:
        return "price_request", 0.82

    return None, 0.0


def classify(subject: str, body: str, sender_email: str = "") -> dict[str, Any]:
    """Hybrid classification with risk gate + narrow deterministic bypass + Grok fallback."""
    t0 = time.perf_counter()

    # 1. Risk / Escalation gate (high recall)
    if _is_risky(subject, body, sender_email):
        return {
            "label": "general_question",  # placeholder; real system would escalate
            "confidence": 0.0,
            "needs_human": True,
            "needs_human_probability": 0.95,
            "needs_human_threshold": NEEDS_HUMAN_THRESHOLD,
            "route": "human",
            "latency_s": time.perf_counter() - t0,
            "cost_usd": 0.0,
            "provider": "hybrid",
            "model": "risk_gate",
        }

    # 2. Narrow deterministic bypass
    det_label, det_conf = _narrow_deterministic_bypass(subject, body)
    if det_label is not None:
        return {
            "label": det_label,
            "confidence": det_conf,
            "needs_human": False,
            "needs_human_probability": 0.15,
            "needs_human_threshold": NEEDS_HUMAN_THRESHOLD,
            "route": "deterministic",
            "latency_s": time.perf_counter() - t0,
            "cost_usd": 0.0,
            "provider": "hybrid",
            "model": "deterministic",
        }

    # 3. Grok fallback (we reuse the frozen llm_existing adapter)
    from approaches import llm_existing as grok

    grok_result = grok.classify(subject, body, sender_email)
    latency = time.perf_counter() - t0

    # Grok confidence is always 1.0 — cannot use for routing
    return {
        "label": grok_result["label"],
        "confidence": grok_result.get("confidence", 1.0),
        "needs_human": grok_result.get("needs_human", False),
        "needs_human_probability": 0.30 if not grok_result.get("needs_human") else 0.70,
        "needs_human_threshold": NEEDS_HUMAN_THRESHOLD,
        "route": "grok",
        "latency_s": latency,
        "cost_usd": grok_result.get("cost_usd", 0.0),
        "provider": "xai",
        "model": grok_result.get("model", "grok-3-mini"),
        "input_tokens": grok_result.get("input_tokens"),
        "output_tokens": grok_result.get("output_tokens"),
        "total_tokens": grok_result.get("total_tokens"),
    }


def estimate_cost(corpus_rows: int) -> dict:
    # Rough estimate: ~30% risk gate, ~8% deterministic bypass, ~62% Grok
    grok_calls = int(corpus_rows * 0.62)
    from approaches import llm_existing as grok
    est = grok.estimate_cost(grok_calls)
    return {
        "model": "hybrid (grok-3-mini + deterministic)",
        "est_grok_calls": grok_calls,
        "est_total_cost_usd": est["est_total_cost_usd"],
        "est_cost_per_1000": round(est["est_total_cost_usd"] / (corpus_rows / 1000), 4),
        "note": "conservative estimate assuming ~62% traffic reaches Grok",
    }