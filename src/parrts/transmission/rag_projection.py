"""RAG projection for transmission hard parts (PARTS project).

Converts canonical catalog + inventory + transmission data into
searchable document text. This is a derived view, not a source of truth.
"""
from __future__ import annotations

from typing import Any


def build_transmission_document(record: dict[str, Any]) -> str:
    """Build rich searchable text from a canonical transmission part record."""
    parts: list[str] = []

    if record.get("name"):
        parts.append(record["name"])

    if record.get("transmission_family"):
        parts.append(f"transmission {record['transmission_family']}")

    if record.get("transmission_variant"):
        parts.append(record["transmission_variant"])

    if record.get("description"):
        parts.append(record["description"])

    # Add identifiers if present
    for ident in record.get("identifiers", []):
        parts.append(f"{ident.get('type', '')} {ident.get('value', '')}")

    if record.get("aliases"):
        parts.extend(record["aliases"])

    if record.get("fitment"):
        for f in record["fitment"]:
            parts.append(f"{f.get('year_from', '')}-{f.get('year_to', '')} {f.get('make', '')} {f.get('model', '')}")

    if record.get("condition"):
        parts.append(record["condition"])

    if record.get("location"):
        parts.append(f"location {record['location']}")

    if record.get("verification_status") == "unverified":
        parts.append("demo data unverified")

    return " ".join(str(p) for p in parts if p).lower()