"""Email desk traffic-light: green auto / yellow review / red urgent human."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EmailTrafficLight:
    color: str  # green | yellow | red
    confidence: float
    reason: str
    actions: list[str] = field(default_factory=list)
    requires_human: bool = True
    auto_send_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def grade_email(
    *,
    classification: str,
    class_confidence: float,
    priority: str,
    specialist_ok: bool,
    parts_tl_color: str | None = None,
    parts_sim: float | None = None,
    parts_stock: int | None = None,
    error: str | None = None,
) -> EmailTrafficLight:
    """
    Product rules (selling point):
      green  — handled, no further action (auto-answer OK)
      yellow — human review required before send / action
      red    — urgent human review (complaint, failure, critical stock/match)
    """
    actions: list[str] = []
    cc = float(class_confidence or 0.0)
    prio = (priority or "medium").lower()
    ctype = (classification or "unknown").lower()
    pcolor = (parts_tl_color or "").lower() or None

    if error:
        return EmailTrafficLight(
            color="red",
            confidence=0.2,
            reason=f"Processing error: {error}",
            actions=["Retry processing", "Assign to parts lead"],
            requires_human=True,
            auto_send_allowed=False,
        )

    if ctype == "complaint" or prio == "urgent":
        return EmailTrafficLight(
            color="red",
            confidence=max(0.75, cc),
            reason="Complaint or urgent priority — escalate immediately",
            actions=[
                "Page duty manager",
                "Do not auto-send",
                "Call customer within 30 minutes",
            ],
            requires_human=True,
            auto_send_allowed=False,
        )

    if not specialist_ok:
        return EmailTrafficLight(
            color="red",
            confidence=0.35,
            reason="Specialist failed to produce a safe response",
            actions=["Manual draft", "Check RAG index health"],
            requires_human=True,
            auto_send_allowed=False,
        )

    # Parts-linked desk mail
    if ctype in ("quote_request", "parts_order", "general_inquiry") and pcolor:
        if pcolor == "red" or (parts_stock is not None and parts_stock <= 0 and (parts_sim or 0) >= 0.3):
            return EmailTrafficLight(
                color="red",
                confidence=min(0.85, 0.45 + cc * 0.4),
                reason="Parts match is red / OOS — human must decide alternate or backorder",
                actions=[
                    "Offer alternate SKU",
                    "Check sister-store transfer",
                    "Call customer with ETA options",
                ],
                requires_human=True,
                auto_send_allowed=False,
            )
        if pcolor == "yellow" or cc < 0.55:
            return EmailTrafficLight(
                color="yellow",
                confidence=min(0.8, 0.4 + cc * 0.4),
                reason="Moderate confidence or yellow parts match — review before send",
                actions=[
                    "Confirm fitment",
                    "Edit suggested reply",
                    "Verify price/stock at counter",
                ],
                requires_human=True,
                auto_send_allowed=False,
            )
        # green parts + strong class
        if pcolor == "green" and cc >= 0.55 and prio in ("low", "medium"):
            return EmailTrafficLight(
                color="green",
                confidence=min(0.98, 0.55 + 0.35 * cc),
                reason="Strong classification and green inventory match — auto-handled",
                actions=[
                    "Auto-send suggested reply",
                    "Log in CRM / email desk",
                    "Optional: reserve stock on confirm",
                ],
                requires_human=False,
                auto_send_allowed=True,
            )
        return EmailTrafficLight(
            color="yellow",
            confidence=0.55,
            reason="Parts-linked email needs light review",
            actions=["Review suggested reply"],
            requires_human=True,
            auto_send_allowed=False,
        )

    # Non-parts specialists
    if ctype in ("shipping_inquiry", "payment_inquiry", "customer_service"):
        if cc >= 0.62 and prio in ("low", "medium", "high"):
            return EmailTrafficLight(
                color="green",
                confidence=min(0.95, cc),
                reason=f"{ctype} answered from specialist playbook",
                actions=["Auto-send FAQ-style reply", "Archive thread"],
                requires_human=False,
                auto_send_allowed=True,
            )
        return EmailTrafficLight(
            color="yellow",
            confidence=max(0.45, cc),
            reason="Specialist reply ready — confirm details",
            actions=["Review tracking/invoice references", "Send after edit"],
            requires_human=True,
            auto_send_allowed=False,
        )

    if cc < 0.45 or ctype == "unknown":
        return EmailTrafficLight(
            color="yellow" if cc >= 0.3 else "red",
            confidence=cc,
            reason="Low classification confidence",
            actions=["Human triage", "Re-classify"],
            requires_human=True,
            auto_send_allowed=False,
        )

    return EmailTrafficLight(
        color="yellow",
        confidence=0.5,
        reason="Default review band",
        actions=actions or ["Human review"],
        requires_human=True,
        auto_send_allowed=False,
    )
