"""Jev shadow classifier (read-only, production-safe).

This module runs Jev in shadow mode only. It never affects production
routing, specialist selection, traffic light, or requires_human.

Configuration:
- Set JEV_SHADOW_ENABLED=1 (or any truthy value) to enable.
- Requires TYPESAFE_API_KEY in the environment.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

# Frozen questions (identical to benchmark)
CATEGORY_QUESTION = Choice(
    instructions="Determine the primary operational intent of this incoming automotive-parts/customer-service inquiry. Select exactly one category based on the customer's main requested action or purpose.",
    criteria={
        "parts_availability": "The customer primarily wants to know whether a specific part or relevant item is available, in stock, obtainable, or can be sourced.",
        "price_request": "The customer primarily wants a price, quote, estimate, or cost for a part or parts.",
        "compatibility_fitment": "The customer primarily wants to know whether a part fits, matches, cross-references, or is compatible with a specific vehicle, configuration, model, or other part.",
        "order_status": "The customer primarily wants information about an existing order, shipment, delivery, tracking status, pickup status, fulfillment, or order progress.",
        "sell_part": "The customer primarily wants to sell, trade, consign, dispose of, or offer parts/items to the business rather than buy them.",
        "general_question": "A legitimate customer inquiry that does not fit the other operational categories, such as hours, location, policies, general service information, or broad questions.",
        "spam_or_irrelevant": "Unsolicited marketing, scams, unrelated solicitations, clearly irrelevant content, malicious/fraudulent outreach, or content that is not a legitimate automotive-parts/customer-service inquiry.",
    },
)

NEEDS_HUMAN_QUESTION = Noul(
    instructions="Does this inquiry require human review rather than safe automatic routing or handling?",
    criteria={
        "true": "Human review is warranted because of meaningful operational risk or customer impact.",
        "false": "The inquiry can reasonably be routed or handled automatically without meaningful safety, financial, legal, customer-relations, or operational risk requiring immediate human judgment.",
    },
)

NEEDS_HUMAN_THRESHOLD = 0.50


def is_shadow_enabled() -> bool:
    val = os.environ.get("JEV_SHADOW_ENABLED", "").strip().lower()
    return val in ("1", "true", "yes", "on")


async def _run_jev(subject: str, body: str, sender_email: str) -> dict[str, Any]:
    state = {
        "subject": subject or "",
        "body": body or "",
        "sender_email": sender_email or "",
    }
    async with AsyncTypeSafeClient() as client:
        resp = await client.system_one(
            model="jev-latest",
            state=state,
            questions={
                "category": CATEGORY_QUESTION,
                "needs_human": NEEDS_HUMAN_QUESTION,
            },
        )

    cat = resp.answers.get("category")
    nh = resp.answers.get("needs_human")

    return {
        "label": getattr(cat, "choice", None),
        "choice_confidence": getattr(cat, "confidence", None),
        "probabilities": getattr(cat, "probabilities", None),
        "noul_probability": getattr(nh, "noul", None),
        "needs_human": getattr(nh, "noul", 0.0) >= NEEDS_HUMAN_THRESHOLD,
        "model": getattr(resp, "model", "jev-latest"),
        "usage": getattr(resp, "usage", None),
    }


def classify_shadow(subject: str, body: str, sender_email: str = "") -> dict[str, Any] | None:
    """Run Jev in shadow mode. Returns None if disabled or on error."""
    if not is_shadow_enabled():
        return None

    if not os.environ.get("TYPESAFE_API_KEY"):
        return None

    try:
        return asyncio.run(_run_jev(subject, body, sender_email))
    except Exception:
        # Never let Jev failure affect production
        return None


def classify_decision(subject: str, body: str, sender_email: str = "") -> dict[str, Any] | None:
    """Run Jev for an explicit decision gate (JEV_DECISION_ENABLED).

    Unlike classify_shadow, this does **not** require JEV_SHADOW_ENABLED.
    Still no-ops without TYPESAFE_API_KEY. Never raises.
    """
    if not os.environ.get("TYPESAFE_API_KEY"):
        return None
    try:
        return asyncio.run(_run_jev(subject, body, sender_email))
    except Exception:
        return None
