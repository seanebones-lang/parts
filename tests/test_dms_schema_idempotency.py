"""DMS SQLite schema initialization must be idempotent."""
from __future__ import annotations

from pathlib import Path

from parrts.dms.service import DmsService


def _column_names(dms: DmsService, table: str) -> set[str]:
    rows = dms.store.fetchall(f"PRAGMA table_info({table})")
    return {str(r["name"]) for r in rows}


def test_ensure_schema_is_idempotent(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()
    dms.ensure_schema()  # must not raise

    catalog_cols = _column_names(dms, "catalog_parts")
    inventory_cols = _column_names(dms, "inventory_levels")

    assert "transmission_family" in catalog_cols
    assert "transmission_variant" in catalog_cols
    assert "verification_status" in catalog_cols
    assert "condition" in inventory_cols


def test_ensure_schema_preserves_existing_data(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()

    dms.store.execute(
        "INSERT INTO catalog_parts "
        "(sku, name, transmission_family, transmission_variant, verification_status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("SCHEMA-IDEM-01", "Schema Idempotency Part", "6L80", "6L80", "unverified"),
    )
    dms.store.commit()

    dms.ensure_schema()  # second init must not wipe or fail

    row = dms.store.fetchone(
        "SELECT sku, name, transmission_family, verification_status "
        "FROM catalog_parts WHERE sku = ?",
        ("SCHEMA-IDEM-01",),
    )
    assert row is not None
    assert row["sku"] == "SCHEMA-IDEM-01"
    assert row["name"] == "Schema Idempotency Part"
    assert row["transmission_family"] == "6L80"
    assert row["verification_status"] == "unverified"


def test_fresh_db_receives_transmission_columns(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()  # single call on brand-new DB

    catalog_cols = _column_names(dms, "catalog_parts")
    inventory_cols = _column_names(dms, "inventory_levels")

    assert "transmission_family" in catalog_cols
    assert "transmission_variant" in catalog_cols
    assert "verification_status" in catalog_cols
    assert "condition" in inventory_cols
