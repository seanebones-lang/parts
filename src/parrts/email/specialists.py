"""Section-expert specialists for inbound parts-desk email (offline-first)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class SpecialistResult:
    ok: bool
    specialist: str
    suggested_response: str
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    parts_traffic_light: str | None = None
    parts_similarity: float | None = None
    parts_stock: int | None = None
    hits: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "specialist": self.specialist,
            "suggested_response": self.suggested_response,
            "data": self.data,
            "message": self.message,
            "parts_traffic_light": self.parts_traffic_light,
            "parts_similarity": self.parts_similarity,
            "parts_stock": self.parts_stock,
            "hits": self.hits,
        }


class Specialist(Protocol):
    name: str

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult: ...


def _greeting(classification: dict[str, Any]) -> str:
    name = (classification.get("extracted_info") or {}).get("customer_name")
    if name:
        return f"Hi {name},"
    return "Hello,"


def _signoff() -> str:
    return (
        "\n\nThank you,\n"
        "Parts Desk — AI-assisted reply\n"
        "(A team member will follow up if anything needs confirmation.)"
    )


def _build_query(subject: str, body: str, classification: dict[str, Any]) -> str:
    info = classification.get("extracted_info") or {}
    bits: list[str] = []
    if info.get("vehicle_info"):
        bits.append(str(info["vehicle_info"]))
    parts = info.get("parts_requested") or []
    bits.extend(str(p) for p in parts)
    skus = info.get("sku_mentions") or []
    bits.extend(str(s) for s in skus)
    if not bits:
        # fall back to subject + first line of body
        bits.append(subject or "")
        first = (body or "").strip().splitlines()
        if first:
            bits.append(first[0][:200])
    return " ".join(b for b in bits if b).strip() or (subject or body or "parts")[:240]


class PartsQuoteSpecialist:
    """Expert: quote / availability using hybrid RAG + traffic light."""

    name = "parts_quote"

    def __init__(self, engine: Any | None = None) -> None:
        self.engine = engine

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        q = _build_query(subject, body, classification)
        hits: list[dict[str, Any]] = []
        tl_color = None
        sim = None
        stock = None
        answer = None
        if self.engine is not None:
            try:
                self.engine.ensure_ready()
                result = self.engine.query(text=q, top_k=5, use_llm=False)
                d = result.to_dict() if hasattr(result, "to_dict") else {}
                hits = list(d.get("hits") or [])
                tl = d.get("traffic_light") or {}
                tl_color = tl.get("color")
                sim = tl.get("similarity")
                stock = tl.get("stock")
                answer = d.get("answer")
            except Exception as exc:
                return SpecialistResult(
                    ok=False,
                    specialist=self.name,
                    suggested_response="",
                    message=f"RAG failed: {exc}",
                )

        lines = [_greeting(classification), "", "Thanks for reaching out about parts availability."]
        if hits:
            lines.append("Here is what I found across our locations:")
            for i, h in enumerate(hits[:5], 1):
                part = h.get("part") or h
                name = part.get("name") or part.get("title") or "Part"
                sku = part.get("sku") or part.get("part_number") or "?"
                loc = part.get("location") or part.get("location_name") or "?"
                stk = part.get("stock", part.get("qty", "?"))
                price = part.get("price", part.get("list_price"))
                price_s = f"${float(price):.2f}" if isinstance(price, (int, float)) else (str(price) if price else "—")
                score = h.get("score")
                score_s = f" (match {float(score):.2f})" if isinstance(score, (int, float)) else ""
                lines.append(f"  {i}. {name} — SKU {sku} @ {loc}, stock {stk}, {price_s}{score_s}")
            if tl_color:
                lines.append(f"\nConfidence band: {tl_color.upper()}.")
            if answer:
                lines.append(str(answer))
            lines.append("Reply YES with the SKU and pickup/ship preference to proceed.")
        else:
            lines.append(
                "I could not find a confident catalog match yet. "
                "Please reply with year/make/model and the part description or OEM number."
            )
            tl_color = tl_color or "red"

        lines.append(_signoff())
        return SpecialistResult(
            ok=True,
            specialist=self.name,
            suggested_response="\n".join(lines),
            data={"query": q},
            message="parts quote drafted",
            parts_traffic_light=tl_color,
            parts_similarity=float(sim) if sim is not None else None,
            parts_stock=int(stock) if stock is not None else None,
            hits=hits,
        )


class PartsOrderSpecialist(PartsQuoteSpecialist):
    name = "parts_order"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        base = super().handle(subject=subject, body=body, classification=classification)
        if not base.ok:
            return base
        extra = (
            "\n\nI can place this as a parts order once you confirm SKU, qty, "
            "and whether this is counter pickup or ship-to."
        )
        base.suggested_response = (base.suggested_response or "") + extra
        base.message = "parts order draft"
        return base


class InventorySpecialist(PartsQuoteSpecialist):
    name = "inventory"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        res = super().handle(subject=subject, body=body, classification=classification)
        res.specialist = self.name
        res.message = "inventory check draft"
        return res


class ShippingSpecialist:
    name = "shipping"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        text = f"{subject}\n{body}".lower()
        lines = [
            _greeting(classification),
            "",
            "Happy to help with shipping.",
            "• Ground parts typically ship same day if ordered before 2pm local.",
            "• Tracking is emailed when the carrier scans the package.",
            "• For freight/oversize, we quote before dispatch.",
        ]
        if "tracking" in text:
            lines.append(
                "If you already have an order number, reply with it and I will pull tracking "
                "(or a teammate will if the label is not in the system yet)."
            )
        lines.append(_signoff())
        return SpecialistResult(
            ok=True,
            specialist=self.name,
            suggested_response="\n".join(lines),
            message="shipping playbook reply",
        )


class PaymentSpecialist:
    name = "payment"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        lines = [
            _greeting(classification),
            "",
            "Thanks for your billing question.",
            "• Invoices are issued when the order is picked/shipped.",
            "• We accept major cards and dealer account terms where set up.",
            "• For a specific invoice, reply with the invoice # and we will attach a copy.",
            "If something looks incorrect, flag the line items and we will audit same day.",
            _signoff(),
        ]
        return SpecialistResult(
            ok=True,
            specialist=self.name,
            suggested_response="\n".join(lines),
            message="payment playbook reply",
        )


class ComplaintSpecialist:
    name = "complaint"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        lines = [
            _greeting(classification),
            "",
            "I'm sorry you're dealing with this — your message has been escalated to a manager.",
            "A human team member will contact you shortly. "
            "Please keep this thread open and include any order #, photos, or timelines that help.",
            "We will not close this until you confirm it is resolved.",
            _signoff(),
        ]
        return SpecialistResult(
            ok=True,
            specialist=self.name,
            suggested_response="\n".join(lines),
            message="complaint escalation draft",
            data={"escalate": True},
        )


class CustomerServiceSpecialist:
    name = "customer_service"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        lines = [
            _greeting(classification),
            "",
            "Thanks for contacting the parts desk.",
            "• Counter hours follow store hours; multi-location stock is searchable in real time.",
            "• Warranty/returns: unopened parts within policy window with receipt.",
            "• For fitment, send year/make/model + part description and we will confirm.",
            _signoff(),
        ]
        return SpecialistResult(
            ok=True,
            specialist=self.name,
            suggested_response="\n".join(lines),
            message="customer service playbook",
        )


class GeneralSpecialist(PartsQuoteSpecialist):
    name = "general"

    def handle(self, *, subject: str, body: str, classification: dict[str, Any]) -> SpecialistResult:
        # Try parts path first; if weak, generic ack
        res = super().handle(subject=subject, body=body, classification=classification)
        res.specialist = self.name
        if not res.hits:
            res.suggested_response = "\n".join(
                [
                    _greeting(classification),
                    "",
                    "Thanks for your email. I've logged it for the parts team.",
                    "If this is about a specific vehicle or part, reply with year/make/model "
                    "and what you need and I'll pull availability.",
                    _signoff(),
                ]
            )
        res.message = "general desk reply"
        return res


def build_specialist_roster(engine: Any | None = None) -> dict[str, Any]:
    return {
        "parts_quote": PartsQuoteSpecialist(engine),
        "parts_order": PartsOrderSpecialist(engine),
        "inventory": InventorySpecialist(engine),
        "shipping": ShippingSpecialist(),
        "payment": PaymentSpecialist(),
        "complaint": ComplaintSpecialist(),
        "customer_service": CustomerServiceSpecialist(),
        "general": GeneralSpecialist(engine),
    }


def run_specialist(
    name: str,
    *,
    subject: str,
    body: str,
    classification: dict[str, Any],
    engine: Any | None = None,
) -> SpecialistResult:
    roster = build_specialist_roster(engine)
    agent = roster.get(name) or roster["general"]
    return agent.handle(subject=subject, body=body, classification=classification)
