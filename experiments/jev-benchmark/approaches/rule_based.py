"""Approach A — deterministic rule-based baseline.

Thin, READ-ONLY adapter over the existing production classifier
``parrts.email.classify.classify_email``. This is the live rule engine the
email desk uses today; we only wrap it so the benchmark measures it without
touching the production file.
"""
from __future__ import annotations

import time
from typing import Any

from labels import CLASSES

# Map production EMAIL_TYPES -> our 7-class taxonomy. Production has no
# dedicated classes for compatibility_fitment, sell_part, or spam; it folds
# them into quote/general. We surface that mapping explicitly so a
# misclassification is reported WITH the production label for diagnosis.
_LLM_CATEGORIES = (  # production EMAIL_TYPES for reference only
    "parts_order", "quote_request", "shipping_inquiry", "complaint",
    "general_inquiry", "payment_inquiry", "customer_service", "unknown",
)

# Deterministic classifiers never fold in a LLM charge / token cost.
_COST_PER_QUERY = 0.0


def _prod_to_target(prod_label: str) -> str:
    """Map classify_email's EMAIL_TYPES label onto the 7-class taxonomy.

    The rule analyzer has no notion of fitment/sell/spam, so multi-intent
    classification here is lossy — which is exactly what the benchmark
    quantifies. Production labels that map cleanly:
      parts_order / quote_request -> price_request (or availability)
      shipping_inquiry / order    -> order_status
      general_inquiry/customer    -> general_question
      (none) -> best-effort
    """
    mapping = {
        "parts_order": "price_request",
        "quote_request": "price_request",
        "shipping_inquiry": "order_status",
        "complaint": "general_question",
        "general_inquiry": "general_question",
        "payment_inquiry": "general_question",
        "customer_service": "general_question",
        "unknown": "general_question",
    }
    return mapping.get(prod_label, "general_question")


def config() -> dict:
    """Static adapter metadata for the benchmark report."""
    return {"name": "rule_based", "cost_per_query": _COST_PER_QUERY, "offline": True}


def classify(subject: str, body: str, sender_email: str = "") -> dict[str, Any]:
    """Run the production rule classifier; return a benchmark-compatible row.

    Returns:
      {
        "label": <7-class target>,
        "confidence": float,
        "needs_human": bool-inferred-from-priority/type,
        "production_label": original EMAIL_TYPES value,
        "latency_s": seconds,
        "cost_usd": 0.0,
      }
    """
    from parrts.email.classify import classify_email  # lazy import: source of truth

    t0 = time.perf_counter()
    c = classify_email(subject=subject, body=body, sender_email=sender_email)
    latency = time.perf_counter() - t0

    target = _prod_to_target(c.classification)
    # needs_human is an adjudication signal. The production classifier flags it
    # via priority/type (complaint/urgent). Benchmark uses it as its own measure.
    needs_human = c.priority == "urgent" or c.classification == "complaint"

    return {
        "label": target,
        "confidence": c.confidence,
        "needs_human": needs_human,
        "production_label": c.classification,
        "production_reasons": list(c.reasons),
        "latency_s": latency,
        "cost_usd": _COST_PER_QUERY,
    }


def estimate_cost(total_rows: int) -> float:
    return 0.0