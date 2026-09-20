"""Frozen Jev adapter (Phase 6).

Uses the official TypeSafe SDK with jev-latest.
Both Choice and Noul are asked in the same system_one request.
Configuration is frozen after smoke test.
"""
import asyncio
import time
from typing import Any
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

# Frozen questions (identical to smoke test)
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
        "true": "Human review is warranted because of meaningful operational risk or customer impact. Examples of the TYPE of situation include serious complaints, safety concerns, fraud or payment disputes, legal/threatening language, explicit request for a manager or person, ambiguous high-impact requests, or situations where automated handling could materially harm the customer or business.",
        "false": "The inquiry can reasonably be routed or handled automatically without meaningful safety, financial, legal, customer-relations, or operational risk requiring immediate human judgment.",
    },
)

NEEDS_HUMAN_THRESHOLD = 0.50  # Frozen threshold


async def _call_jev(state: dict) -> dict:
    t0 = time.perf_counter()
    async with AsyncTypeSafeClient() as client:
        resp = await client.system_one(
            model="jev-latest",
            state=state,
            questions={
                "category": CATEGORY_QUESTION,
                "needs_human": NEEDS_HUMAN_QUESTION,
            },
        )
    latency = time.perf_counter() - t0

    cat = resp.answers.get("category")
    nh = resp.answers.get("needs_human")

    result = {
        "label": cat.choice if cat else None,
        "choice_confidence": getattr(cat, "confidence", None),
        "probabilities": getattr(cat, "probabilities", None),
        "noul_probability": getattr(nh, "noul", None),
        "needs_human": getattr(nh, "noul", 0) >= NEEDS_HUMAN_THRESHOLD,
        "latency_s": latency,
        "usage": getattr(resp, "usage", None),
        "model": getattr(resp, "model", "jev-latest"),
    }
    return result


def classify(subject: str, body: str, sender_email: str = "") -> dict[str, Any]:
    """Synchronous wrapper for the frozen Jev adapter."""
    state = {
        "subject": subject or "",
        "body": body or "",
        "sender_email": sender_email or "",
    }
    return asyncio.run(_call_jev(state))