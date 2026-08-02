"""Offline rule-based inbound email classifier (no LLM required)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

EMAIL_TYPES = (
    "parts_order",
    "quote_request",
    "shipping_inquiry",
    "complaint",
    "general_inquiry",
    "payment_inquiry",
    "customer_service",
    "unknown",
)

DEPARTMENTS = ("parts", "service", "sales", "admin", "shipping", "billing")


@dataclass
class Classification:
    classification: str
    confidence: float
    department: str
    priority: str  # low | medium | high | urgent
    extracted_info: dict[str, Any] = field(default_factory=dict)
    specialist: str = "general"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_RULES: list[tuple[str, str, str, list[str], float]] = [
    # type, department, specialist, keywords, weight
    ("complaint", "admin", "complaint", [
        "complaint", "lawsuit", "attorney", "refund now", "unacceptable",
        "furious", "manager", "bbb", "better business", "scam", "ripoff",
        "never again", "worst", "angry",
    ], 1.4),
    ("payment_inquiry", "billing", "payment", [
        "invoice", "payment", "paid", "billing", "charge", "credit card",
        "receipt", "refund", "overcharged", "statement", "ach", "wire",
    ], 1.1),
    ("shipping_inquiry", "shipping", "shipping", [
        "shipping", "delivery", "tracking", "ups", "fedex", "ship",
        "eta", "arrive", "freight", "label", "carrier", "in transit",
    ], 1.1),
    ("parts_order", "parts", "parts_order", [
        "order", "please order", "need to buy", "purchase", "ship me",
        "place an order", "want to order", "qty", "quantity",
    ], 1.0),
    ("quote_request", "parts", "parts_quote", [
        "quote", "price", "how much", "pricing", "availability",
        "do you have", "looking for", "need a price", "cost for",
        "brake", "filter", "rotor", "pad", "spark", "oem", "part number",
        "sku", "fitment", "compatible",
    ], 0.95),
    ("customer_service", "parts", "customer_service", [
        "hours", "open", "location", "address", "phone", "speak to",
        "appointment", "warranty", "return policy",
    ], 0.9),
]

_VEHICLE_RE = re.compile(
    r"\b((?:19|20)\d{2})\s+([A-Za-z][A-Za-z\-]+)\s+([A-Za-z0-9][A-Za-z0-9\-]+)",
    re.I,
)
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SKU_RE = re.compile(r"\b(?:SKU|P/?N|PART\s*#?)\s*[:#]?\s*([A-Z0-9][-A-Z0-9]{3,})\b", re.I)
_QTY_RE = re.compile(r"\b(?:qty|quantity|x)\s*[:=]?\s*(\d{1,3})\b", re.I)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_entities(subject: str, body: str) -> dict[str, Any]:
    blob = f"{subject or ''}\n{body or ''}"
    info: dict[str, Any] = {
        "customer_name": None,
        "phone": None,
        "vehicle_info": None,
        "parts_requested": [],
        "quantity": None,
        "sku_mentions": [],
        "urgency": "normal",
    }
    m = _VEHICLE_RE.search(blob)
    if m:
        info["vehicle_info"] = f"{m.group(1)} {m.group(2).title()} {m.group(3).title()}"
    phones = _PHONE_RE.findall(blob)
    if phones:
        info["phone"] = phones[0]
    skus = _SKU_RE.findall(blob)
    if skus:
        info["sku_mentions"] = list(dict.fromkeys(skus))
    qm = _QTY_RE.search(blob)
    if qm:
        info["quantity"] = int(qm.group(1))

    # crude part noun phrases from common categories
    parts: list[str] = []
    for pat in (
        r"brake pads?",
        r"brake rotors?",
        r"oil filter",
        r"air filter",
        r"spark plugs?",
        r"wiper blades?",
        r"battery",
        r"alternator",
        r"starter",
        r"cabin filter",
        r"timing belt",
        r"water pump",
    ):
        if re.search(pat, blob, re.I):
            parts.append(re.search(pat, blob, re.I).group(0).lower())  # type: ignore[union-attr]
    info["parts_requested"] = list(dict.fromkeys(parts))

    low = blob.lower()
    if any(w in low for w in ("asap", "urgent", "immediately", "today", "emergency")):
        info["urgency"] = "urgent"
    return info


def classify_email(subject: str = "", body: str = "", sender_email: str = "") -> Classification:
    """Score keyword rules; return best type + specialist routing."""
    text = _norm(f"{subject} {body} {sender_email}")
    scores: dict[str, float] = {t: 0.0 for t in EMAIL_TYPES}
    hit_reasons: dict[str, list[str]] = {t: [] for t in EMAIL_TYPES}
    specialist_map = {t: "general" for t in EMAIL_TYPES}
    dept_map = {t: "parts" for t in EMAIL_TYPES}

    for etype, dept, specialist, kws, weight in _RULES:
        for kw in kws:
            if kw in text:
                scores[etype] += weight
                hit_reasons[etype].append(kw)
        specialist_map[etype] = specialist
        dept_map[etype] = dept

    # boost quote if vehicle + part language without strong order words
    extracted = extract_entities(subject, body)
    if extracted.get("vehicle_info") and extracted.get("parts_requested"):
        scores["quote_request"] += 0.8
        hit_reasons["quote_request"].append("vehicle+part")
    if extracted.get("sku_mentions"):
        scores["quote_request"] += 0.5
        scores["parts_order"] += 0.3

    best = max(scores, key=lambda k: scores[k])
    best_score = scores[best]
    if best_score <= 0:
        best = "general_inquiry"
        best_score = 0.35
        hit_reasons[best] = ["fallback"]
        specialist_map[best] = "general"
        dept_map[best] = "parts"

    # normalize confidence 0.35–0.98
    conf = min(0.98, 0.4 + 0.12 * best_score)
    if len(hit_reasons.get(best, [])) >= 3:
        conf = min(0.98, conf + 0.08)

    priority = "medium"
    if best == "complaint" or extracted.get("urgency") == "urgent":
        priority = "urgent"
        conf = max(conf, 0.7)
    elif best in ("shipping_inquiry", "payment_inquiry") and best_score >= 2:
        priority = "high"
    elif best_score < 1:
        priority = "low"

    return Classification(
        classification=best,
        confidence=round(conf, 4),
        department=dept_map.get(best, "parts"),
        priority=priority,
        extracted_info=extracted,
        specialist=specialist_map.get(best, "general"),
        reasons=hit_reasons.get(best, [])[:12],
    )
