"""Traffic-light policy: stock × similarity → green/yellow/red + actions."""

from __future__ import annotations

from parrts.models import PartRecord, RankedHit, TrafficLight

# Thresholds from backlog / task brief
SIM_GREEN = 0.55
SIM_LOW = 0.30
STOCK_GREEN = 3


def evaluate_traffic_light(
    similarity: float,
    stock: int,
    *,
    part: PartRecord | None = None,
    location_filter: str | None = None,
) -> TrafficLight:
    """
    green if sim>=0.55 and stock>=3
    yellow if stock 1-2 or mid sim
    red if stock 0 or low sim
    """
    sim = float(similarity)
    stk = int(stock)
    actions: list[str] = []

    if sim < SIM_LOW:
        color = "red"
        confidence = max(0.05, min(0.35, sim + 0.1))
        reason = f"Low semantic match (sim={sim:.2f} < {SIM_LOW})"
        actions = [
            "Ask user to clarify make/model/year/part",
            "Expand search without location filter" if location_filter else "Try alternate part synonyms",
            "Escalate to human parts specialist",
        ]
    elif stk <= 0:
        color = "red"
        confidence = min(0.75, 0.4 + sim * 0.4)
        reason = f"Match found but out of stock (sim={sim:.2f}, stock=0)"
        actions = [
            "Check other locations for same SKU family",
            "Offer compatible alternate part",
            "Create backorder / notify when available",
        ]
        if part:
            actions.append(f"Search transfer options for {part.sku}")
    elif sim >= SIM_GREEN and stk >= STOCK_GREEN:
        color = "green"
        confidence = min(0.99, 0.55 + 0.35 * sim + 0.02 * min(stk, 10))
        reason = f"Strong match with healthy stock (sim={sim:.2f}, stock={stk})"
        actions = [
            "Reserve inventory",
            "Quote price and confirm location",
            "Offer checkout / shipping label",
        ]
    elif stk in (1, 2) or (SIM_LOW <= sim < SIM_GREEN):
        color = "yellow"
        # mid confidence
        conf = 0.4 + 0.3 * sim
        if stk in (1, 2):
            conf = min(conf, 0.55 + 0.1 * sim)
        confidence = min(0.8, conf)
        reasons = []
        if stk in (1, 2):
            reasons.append(f"low stock ({stk})")
        if SIM_LOW <= sim < SIM_GREEN:
            reasons.append(f"moderate similarity ({sim:.2f})")
        reason = "Review needed: " + ", ".join(reasons) if reasons else "Review needed"
        actions = [
            "Confirm fitment with customer",
            "Double-check interchange / year range",
        ]
        if stk in (1, 2):
            actions.append("Hold last units and offer transfer from sister store")
        if sim < SIM_GREEN:
            actions.append("Verify part name matches request before quoting")
    else:
        # Fallback catch-all → yellow
        color = "yellow"
        confidence = 0.5
        reason = f"Uncategorized mid-band (sim={sim:.2f}, stock={stk})"
        actions = ["Manual review"]

    return TrafficLight(
        color=color,
        confidence=round(float(confidence), 4),
        actions=actions,
        reason=reason,
        similarity=round(sim, 4),
        stock=stk,
    )


def policy_for_hits(
    hits: list[RankedHit],
    location_filter: str | None = None,
) -> TrafficLight:
    """Apply policy to the top hit (or red if empty)."""
    if not hits:
        return TrafficLight(
            color="red",
            confidence=0.1,
            actions=[
                "No inventory matches — rephrase query",
                "Escalate to human parts specialist",
            ],
            reason="No retrieval hits",
            similarity=0.0,
            stock=0,
        )
    top = hits[0]
    return evaluate_traffic_light(
        similarity=top.score,
        stock=top.part.stock,
        part=top.part,
        location_filter=location_filter,
    )
