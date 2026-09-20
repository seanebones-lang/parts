"""Idempotent synthetic demo seed loader for PARTS transmission vertical.

All data is marked as demo/unverified.
"""
from __future__ import annotations

from datetime import datetime, timezone

from parrts.dms.service import DmsService
from .seed import (
    DEMO_CATALOG_PARTS,
    DEMO_FITMENTS,
    DEMO_IDENTIFIERS,
    DEMO_INTERCHANGES,
    DEMO_INVENTORY,
    DEMO_TRANSMISSION_FAMILIES,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_demo_seed(dms: DmsService, *, force: bool = False) -> dict[str, int]:
    """Load synthetic 6L80/6L90 demo data into the canonical DMS.

    Returns counts of inserted/updated records.
    """
    counts = {
        "transmission_families": 0,
        "catalog_parts": 0,
        "identifiers": 0,
        "fitments": 0,
        "interchanges": 0,
        "inventory": 0,
    }

    # 1. Transmission families
    for fam in DEMO_TRANSMISSION_FAMILIES:
        existing = dms.store.fetchone(
            "SELECT family FROM transmission_families WHERE family = ?", (fam["family"],)
        )
        if existing is None:
            dms.store.execute(
                """INSERT INTO transmission_families 
                   (family, manufacturer, notes, created_at) VALUES (?, ?, ?, ?)""",
                (fam["family"], fam.get("manufacturer", ""), fam.get("notes", ""), _now()),
            )
            counts["transmission_families"] += 1

    # 2. Catalog parts (with transmission columns)
    for part in DEMO_CATALOG_PARTS:
        existing = dms.store.fetchone("SELECT sku FROM catalog_parts WHERE sku = ?", (part["sku"],))
        if existing is None:
            dms.store.execute(
                """INSERT INTO catalog_parts 
                   (sku, name, description, category, oem_brand, list_price, source, 
                    transmission_family, transmission_variant, verification_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    part["sku"],
                    part["name"],
                    part.get("description", ""),
                    part.get("category", "transmission_hard_parts"),
                    part.get("oem_brand", ""),
                    part.get("list_price", 0),
                    part.get("source", "demo_seed"),
                    part.get("transmission_family", ""),
                    part.get("transmission_variant", ""),
                    part.get("verification_status", "unverified"),
                ),
            )
            counts["catalog_parts"] += 1

    # 3. Identifiers
    for ident in DEMO_IDENTIFIERS:
        existing = dms.store.fetchone(
            """SELECT id FROM part_identifiers 
               WHERE sku = ? AND identifier_type = ? AND identifier_value = ?""",
            (ident["sku"], ident["identifier_type"], ident["identifier_value"]),
        )
        if existing is None:
            dms.store.execute(
                """INSERT INTO part_identifiers 
                   (sku, identifier_type, identifier_value, notes, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (ident["sku"], ident["identifier_type"], ident["identifier_value"], "", _now()),
            )
            counts["identifiers"] += 1

    # 4. Fitments
    for fit in DEMO_FITMENTS:
        existing = dms.store.fetchone(
            "SELECT id FROM part_fitments WHERE sku = ? AND make = ? AND model = ?",
            (fit["sku"], fit.get("make"), fit.get("model")),
        )
        if existing is None:
            dms.store.execute(
                """INSERT INTO part_fitments 
                   (sku, year_from, year_to, make, model, engine, transmission_family, 
                    verification_status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fit["sku"],
                    fit.get("year_from"),
                    fit.get("year_to"),
                    fit.get("make"),
                    fit.get("model"),
                    fit.get("engine"),
                    fit.get("transmission_family"),
                    fit.get("verification_status", "unverified"),
                    _now(),
                ),
            )
            counts["fitments"] += 1

    # 5. Interchanges
    for inter in DEMO_INTERCHANGES:
        existing = dms.store.fetchone(
            """SELECT id FROM part_interchanges 
               WHERE source_sku = ? AND target_sku = ? AND relationship_type = ?""",
            (inter["source_sku"], inter["target_sku"], inter["relationship_type"]),
        )
        if existing is None:
            dms.store.execute(
                """INSERT INTO part_interchanges 
                   (source_sku, target_sku, relationship_type, confidence, notes, 
                    verification_status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    inter["source_sku"],
                    inter["target_sku"],
                    inter["relationship_type"],
                    inter.get("confidence", 0.0),
                    inter.get("notes", "demo data"),
                    inter.get("verification_status", "unverified"),
                    _now(),
                ),
            )
            counts["interchanges"] += 1

    # 6. Inventory (requires locations)
    # Note: ensure_schema() may be called multiple times; ALTERs are handled in store.py
    # but we avoid calling it repeatedly here to prevent duplicate column errors in SQLite.
    for inv in DEMO_INVENTORY:
        loc_row = dms.store.fetchone("SELECT id FROM locations WHERE code = ?", (inv["location"],))
        if loc_row is None:
            continue
        loc_id = loc_row["id"]
        existing = dms.store.fetchone(
            "SELECT qty FROM inventory_levels WHERE sku = ? AND location_id = ?",
            (inv["sku"], loc_id),
        )
        if existing is None:
            dms.store.execute(
                """INSERT INTO inventory_levels (sku, location_id, qty, condition)
                   VALUES (?, ?, ?, ?)""",
                (inv["sku"], loc_id, inv["qty"], inv.get("condition", "new")),
            )
            counts["inventory"] += 1

    dms.store.commit()
    return counts