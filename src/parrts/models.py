"""Core data models for parrts inventory and retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TrafficColor(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True)
class PartRecord:
    """A single part at a single location."""

    sku: str
    name: str
    location: str
    stock: int
    price: float
    description: str = ""
    make: str = ""
    model: str = ""
    year: str = ""
    category: str = ""

    def document_text(self) -> str:
        """Text used for embedding / BM25 indexing."""
        bits = [
            self.name,
            self.description,
            self.make,
            self.model,
            self.year,
            self.category,
            self.sku,
            self.location,
            f"stock {self.stock}",
            f"price {self.price}",
        ]
        return " ".join(b for b in bits if b).strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PartRecord:
        return cls(
            sku=str(data["sku"]),
            name=str(data["name"]),
            location=str(data["location"]),
            stock=int(data["stock"]),
            price=float(data["price"]),
            description=str(data.get("description", "")),
            make=str(data.get("make", "")),
            model=str(data.get("model", "")),
            year=str(data.get("year", "")),
            category=str(data.get("category", "")),
        )


@dataclass
class LocationInventory:
    """Inventory snapshot for one or all locations."""

    locations: dict[str, list[PartRecord]] = field(default_factory=dict)

    def all_parts(self) -> list[PartRecord]:
        parts: list[PartRecord] = []
        for loc_parts in self.locations.values():
            parts.extend(loc_parts)
        return parts

    def filter_location(self, location: str | None) -> list[PartRecord]:
        if not location:
            return self.all_parts()
        key = location.strip().lower()
        for name, parts in self.locations.items():
            if name.lower() == key or key in name.lower():
                return list(parts)
        return []

    def summary(self) -> dict[str, Any]:
        total_skus = 0
        total_units = 0
        loc_stats: dict[str, dict[str, int]] = {}
        for name, parts in self.locations.items():
            units = sum(p.stock for p in parts)
            loc_stats[name] = {"skus": len(parts), "units": units}
            total_skus += len(parts)
            total_units += units
        return {
            "locations": len(self.locations),
            "total_skus": total_skus,
            "total_units": total_units,
            "by_location": loc_stats,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            name: [p.to_dict() for p in parts] for name, parts in self.locations.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LocationInventory:
        locations: dict[str, list[PartRecord]] = {}
        for name, items in data.items():
            locations[name] = [PartRecord.from_dict(item) for item in items]
        return cls(locations=locations)


@dataclass
class TrafficLight:
    """Stock × similarity policy outcome."""

    color: str  # green | yellow | red
    confidence: float
    actions: list[str] = field(default_factory=list)
    reason: str = ""
    similarity: float = 0.0
    stock: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RankedHit:
    """A single retrieval hit before/after policy."""

    part: PartRecord
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = self.part.to_dict()
        d.update(
            {
                "score": self.score,
                "dense_score": self.dense_score,
                "sparse_score": self.sparse_score,
                "rrf_score": self.rrf_score,
            }
        )
        return d


@dataclass
class QueryResult:
    """Full query response for CLI/API consumers."""

    query: str
    hits: list[RankedHit] = field(default_factory=list)
    traffic_light: TrafficLight | None = None
    answer: str | None = None
    location_filter: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "location_filter": self.location_filter,
            "hits": [h.to_dict() for h in self.hits],
            "traffic_light": self.traffic_light.to_dict() if self.traffic_light else None,
            "answer": self.answer,
            "meta": self.meta,
        }
