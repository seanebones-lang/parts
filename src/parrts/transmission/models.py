"""Domain models for transmission hard-parts vertical.

These are lightweight, typed representations used by the transmission
intelligence layer. They are not a second source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Condition = Literal["new", "used", "rebuilt", "core"]
VerificationStatus = Literal["unverified", "verified", "disputed"]
RelationshipType = Literal["interchangeable", "supersedes", "core_exchange", "not_interchangeable"]


@dataclass(frozen=True)
class TransmissionFamily:
    family: str
    manufacturer: str = ""
    notes: str = ""


@dataclass(frozen=True)
class PartIdentifier:
    sku: str
    identifier_type: str          # oem, casting, aftermarket, common_name, abbreviation
    identifier_value: str
    notes: str = ""


@dataclass(frozen=True)
class PartInterchange:
    source_sku: str
    target_sku: str
    relationship_type: RelationshipType
    confidence: float = 0.0
    notes: str = ""
    source: str = ""
    verification_status: VerificationStatus = "unverified"


@dataclass(frozen=True)
class PartFitment:
    sku: str
    year_from: int | None = None
    year_to: int | None = None
    make: str | None = None
    model: str | None = None
    engine: str | None = None
    transmission_family: str | None = None
    transmission_variant: str | None = None
    verification_status: VerificationStatus = "unverified"


@dataclass
class TransmissionInquiryResult:
    """Structured result returned by the deterministic resolver."""
    query: str
    transmission_family: str | None = None
    part_type: str | None = None
    year: int | None = None
    make: str | None = None
    model: str | None = None
    matched_skus: list[str] = field(default_factory=list)
    fitment_status: str = "unknown"          # exact | compatible | candidate | insufficient | no_match
    inventory_available: bool = False
    aliases_found: list[str] = field(default_factory=list)
    interchange_candidates: list[str] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)
    notes: str = ""