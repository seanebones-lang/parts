"""Transmission-mode email inventory authority — DMS + counter_search only.

NEVER uses PartsRAGEngine, parrts.inventory, or the legacy Chicago demo catalog.
If DMS / counter_search cannot answer safely → human review (no generic fallback).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from parrts.dms.service import DmsService
from parrts.transmission.counter_search import CounterSearchResult, counter_search

# Location display aliases (UI-only; codes unchanged)
_LOC_ALIAS = {
    "CHI-N": "Main Warehouse",
    "OHARE": "Front Counter",
}


def _loc_label(code: str | None, name: str | None = None) -> str:
    c = (code or "").strip()
    if c in _LOC_ALIAS:
        return f"{_LOC_ALIAS[c]} ({c})"
    if name and c:
        return f"{name} ({c})"
    return name or c or "—"


@dataclass
class TransmissionQueryResult:
    """Mimics engine.query().to_dict() shape used by email specialists/pipeline."""

    answer: str
    hits: list[dict[str, Any]] = field(default_factory=list)
    traffic_light: dict[str, Any] = field(default_factory=dict)
    search_mode: str = "needs_review"
    query: str = ""
    inventory_source: str = "transmission_dms"
    human_readable: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "hits": self.hits,
            "traffic_light": self.traffic_light,
            "search_mode": self.search_mode,
            "query": self.query,
            "inventory_source": self.inventory_source,
            "human_readable": self.human_readable,
            "error": self.error,
        }


class TransmissionPartsAdapter:
    """Drop-in inventory backend for email specialists in transmission vertical."""

    is_transmission_adapter = True
    inventory_source = "transmission_dms"

    def __init__(self, root: Path | str, dms: DmsService | None = None) -> None:
        self.root = Path(root).resolve()
        self._dms = dms
        self._ready = False
        self._init_error: str | None = None

    def ensure_ready(self) -> None:
        if self._ready and self._dms is not None:
            return
        try:
            if self._dms is None:
                self._dms = DmsService(self.root)
            # Non-mutating readiness: catalog must exist
            row = self._dms.store.fetchone("SELECT COUNT(*) AS n FROM catalog_parts")
            n = int(row["n"]) if row else 0
            if n <= 0:
                self._init_error = "Transmission DMS has no catalog rows"
                self._ready = False
                return
            self._init_error = None
            self._ready = True
        except Exception as exc:  # noqa: BLE001
            self._init_error = f"Transmission DMS unavailable: {exc}"
            self._ready = False
            self._dms = None

    def query(self, text: str = "", top_k: int = 5, use_llm: bool = False) -> TransmissionQueryResult:
        """Run counter_search; never fall back to generic RAG."""
        _ = use_llm
        self.ensure_ready()
        q = (text or "").strip()
        if self._init_error or self._dms is None:
            return TransmissionQueryResult(
                answer=(
                    "Thanks for the request. We could not reach the transmission inventory "
                    "system safely, so a parts team member must review this before we confirm "
                    "availability or SKU."
                ),
                hits=[],
                traffic_light={
                    "color": "yellow",
                    "similarity": None,
                    "stock": None,
                    "reason": self._init_error or "dms_unavailable",
                },
                search_mode="needs_review",
                query=q,
                human_readable=self._init_error,
                error=self._init_error,
            )
        try:
            result = counter_search(q, self._dms)
        except Exception as exc:  # noqa: BLE001
            return TransmissionQueryResult(
                answer=(
                    "Thanks for the request. Transmission inventory lookup failed. "
                    "A team member will follow up — we will not guess a part from another catalog."
                ),
                hits=[],
                traffic_light={
                    "color": "yellow",
                    "similarity": None,
                    "stock": None,
                    "reason": f"counter_search_error:{exc}",
                },
                search_mode="needs_review",
                query=q,
                error=str(exc),
            )
        return _format_counter_result(result, top_k=top_k)


def _hit_from_inventory_row(row: dict[str, Any], *, sku: str, name: str | None, family: str | None) -> dict[str, Any]:
    code = str(row.get("location_code") or row.get("location") or "")
    return {
        "sku": sku,
        "name": name or sku,
        "family": family,
        "variant": row.get("transmission_variant") or row.get("variant"),
        "condition": row.get("condition"),
        "location_code": code,
        "location_name": _loc_label(code, row.get("location_name")),
        "location": _loc_label(code, row.get("location_name")),
        "bin": row.get("bin"),
        "on_hand": row.get("on_hand", row.get("qty")),
        "reserved": row.get("reserved", row.get("reserved_qty")),
        "available": row.get("available", row.get("qty")),
        "stock": row.get("available", row.get("qty")),
        "identifier": None,
        "part": {
            "sku": sku,
            "name": name or sku,
            "location": _loc_label(code, row.get("location_name")),
            "location_code": code,
            "stock": row.get("available", row.get("qty")),
            "qty": row.get("available", row.get("qty")),
        },
    }


def _hit_from_candidate(c: dict[str, Any]) -> dict[str, Any]:
    code = str(c.get("location_code") or "")
    name = c.get("name") or c.get("sku")
    sku = str(c.get("sku") or "")
    return {
        "sku": sku,
        "name": name,
        "family": c.get("transmission_family"),
        "variant": c.get("transmission_variant"),
        "condition": c.get("condition"),
        "location_code": code,
        "location_name": _loc_label(code, c.get("location_name")),
        "location": _loc_label(code, c.get("location_name")),
        "bin": c.get("bin"),
        "on_hand": c.get("on_hand"),
        "reserved": c.get("reserved"),
        "available": c.get("available"),
        "stock": c.get("available"),
        "identifier": c.get("casting_or_id"),
        "actual_part_category": c.get("actual_part_category") or c.get("part_type_label"),
        "part": {
            "sku": sku,
            "name": name,
            "location": _loc_label(code, c.get("location_name")),
            "location_code": code,
            "stock": c.get("available"),
            "qty": c.get("available"),
            "condition": c.get("condition"),
        },
    }


def _format_counter_result(result: CounterSearchResult, *, top_k: int = 5) -> TransmissionQueryResult:
    mode = result.search_mode or "needs_review"
    q = result.query or ""

    if mode == "exact_match" and result.sku:
        hits: list[dict[str, Any]] = []
        inv_rows = result.inventory or []
        if inv_rows:
            for row in inv_rows[: max(top_k, 5)]:
                hits.append(
                    _hit_from_inventory_row(
                        row if isinstance(row, dict) else dict(row),
                        sku=str(result.sku),
                        name=result.name,
                        family=result.transmission_family,
                    )
                )
        else:
            hits.append(
                {
                    "sku": result.sku,
                    "name": result.name or result.sku,
                    "family": result.transmission_family,
                    "location": "—",
                    "stock": result.aggregate_available,
                    "available": result.aggregate_available,
                    "part": {
                        "sku": result.sku,
                        "name": result.name or result.sku,
                        "stock": result.aggregate_available,
                        "qty": result.aggregate_available,
                    },
                }
            )
        stock_total = int(result.aggregate_available or 0)
        lines = [
            f"Thanks for reaching out about the {result.name or result.sku}.",
            "",
            "I found:",
            f"{result.name or 'Part'}",
            f"SKU: {result.sku}",
        ]
        if result.transmission_family:
            lines.append(f"Transmission family: {result.transmission_family}")
        lines.append("")
        if inv_rows:
            for row in inv_rows[:8]:
                rd = row if isinstance(row, dict) else dict(row)
                code = str(rd.get("location_code") or rd.get("location") or "")
                avail = rd.get("available", rd.get("qty", 0))
                lines.append(f"{_loc_label(code, rd.get('location_name'))}: {avail} available")
        else:
            lines.append(f"Aggregate available: {stock_total}")
        lines.extend(
            [
                "",
                "We can prepare this for counter pickup or add it to a quote.",
                "A team member should confirm final fitment before shipment where appropriate.",
            ]
        )
        color = "green" if stock_total > 0 else "yellow"
        return TransmissionQueryResult(
            answer="\n".join(lines),
            hits=hits,
            traffic_light={
                "color": color,
                "similarity": 0.99,
                "stock": stock_total,
                "reason": f"exact_match:{result.sku}",
            },
            search_mode="exact_match",
            query=q,
            human_readable=result.human_readable,
        )

    if mode == "inventory_matches" and result.discovery:
        disc = result.discovery
        cands = list(disc.get("candidates") or [])[: max(top_k, 6)]
        hits = [_hit_from_candidate(c if isinstance(c, dict) else dict(c)) for c in cands]
        n = int(disc.get("candidate_count") or len(hits))
        fam = disc.get("family") or result.transmission_family or ""
        ptype = disc.get("part_type") or result.part_type or "part"
        lines = [
            f"Thanks for reaching out about {fam} {ptype}.".strip(),
            "",
            f"We found {n} matching inventory lot(s) in our transmission stock.",
            "",
        ]
        for i, h in enumerate(hits, 1):
            lines.append(f"{i}.")
            lines.append(f"SKU: {h.get('sku')}")
            if h.get("name"):
                lines.append(str(h["name"]))
            if h.get("condition"):
                lines.append(f"Condition: {h['condition']}")
            lines.append(f"Location: {h.get('location') or h.get('location_name')}")
            lines.append(f"Available: {h.get('available')}")
            lines.append("")
        lines.extend(
            [
                "Several matching inventory records are available. "
                "A parts team member should select the correct unit before the order is finalized.",
                "This is not an automatic single-SKU resolve.",
            ]
        )
        avail = int(disc.get("total_available") or 0)
        return TransmissionQueryResult(
            answer="\n".join(lines).strip(),
            hits=hits,
            traffic_light={
                "color": "yellow",
                "similarity": None,
                "stock": avail,
                "reason": "inventory_matches_multi_lot",
            },
            search_mode="inventory_matches",
            query=q,
            human_readable=result.human_readable,
        )

    # needs_review (or empty)
    reason = (result.human_readable or result.ambiguity_reason or "needs_review").strip()
    lines = [
        "Thanks for the request. We need one more piece of information before confirming the correct part.",
        "",
    ]
    if reason:
        lines.append(reason)
        lines.append("")
    lines.append(
        "Please reply with the transmission family (e.g. 6L80 vs 6L90), the exact part type "
        "(pump, valve body, drum, core, …), and any OEM/casting number if you have it. "
        "We will not recommend an unrelated part."
    )
    # Urgency: ASAP/overnight → yellow still for safety (policy may promote red via grade_email)
    return TransmissionQueryResult(
        answer="\n".join(lines),
        hits=[],
        traffic_light={
            "color": "yellow",
            "similarity": None,
            "stock": None,
            "reason": reason[:240] or "needs_review",
        },
        search_mode="needs_review",
        query=q,
        human_readable=reason,
    )
