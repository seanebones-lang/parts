"""Phase 9 — safe transmission pilot CSV import."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from parrts.cli import main as cli_main
from parrts.dms.service import DmsService
from parrts.transmission.importer import (
    build_import_plan,
    commit_import_plan,
    commit_transmission_import,
    preview_transmission_import,
)
from parrts.transmission.seed_loader import load_demo_seed


VALID_CSV = """sku,name,transmission_family,location,qty,condition,bin,part_type,identifier_type,identifier_value
PILOT-PUMP-01,6L80 Pilot Pump Assembly,6L80,CHI-N,4,new,P-01,pump,oem,PILOT-OEM-001
"""

ZERO_CSV = """sku,name,transmission_family,location,qty,condition,bin,part_type
PILOT-ZERO-01,6L80 Zero Stock Pump,6L80,CHI-N,0,new,Z-01,pump
"""


@pytest.fixture
def dms_root(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()  # creates default locations including CHI-N
    return tmp_path, dms


@pytest.fixture
def seeded(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()
    load_demo_seed(dms)
    return tmp_path, dms


def _counts(dms: DmsService) -> dict[str, int]:
    cat = dms.store.fetchone("SELECT COUNT(*) AS c FROM catalog_parts")
    inv = dms.store.fetchone("SELECT COUNT(*) AS c FROM inventory_levels")
    ids = dms.store.fetchone("SELECT COUNT(*) AS c FROM part_identifiers")
    locs = dms.store.fetchone("SELECT COUNT(*) AS c FROM locations")
    return {
        "catalog": int(cat["c"]) if cat else 0,
        "inventory": int(inv["c"]) if inv else 0,
        "identifiers": int(ids["c"]) if ids else 0,
        "locations": int(locs["c"]) if locs else 0,
    }


def test_phase9_preview_is_read_only(dms_root):
    root, dms = dms_root
    before = _counts(dms)
    result = preview_transmission_import(VALID_CSV, dms, source="jp-test")
    assert result["mode"] == "preview"
    assert result["ok"] is True
    assert result["valid_rows"] == 1
    assert result["new_sku_count"] == 1
    assert result["inventory_inserts"] == 1
    assert result["committed"] is False
    assert _counts(dms) == before


def test_phase9_explicit_commit(dms_root):
    root, dms = dms_root
    result = commit_transmission_import(VALID_CSV, dms, source="jp-test")
    assert result["mode"] == "commit"
    assert result["committed"] is True
    assert result["ok"] is True

    part = dms.store.fetchone(
        "SELECT sku, name, transmission_family, verification_status, source "
        "FROM catalog_parts WHERE sku = ?",
        ("PILOT-PUMP-01",),
    )
    assert part is not None
    assert part["transmission_family"] == "6L80"
    assert part["verification_status"] == "unverified"
    assert "pilot_csv" in str(part["source"])

    inv = dms.store.fetchone(
        """
        SELECT i.qty, i.condition, i.bin, l.code
        FROM inventory_levels i
        JOIN locations l ON l.id = i.location_id
        WHERE i.sku = ?
        """,
        ("PILOT-PUMP-01",),
    )
    assert inv is not None
    assert inv["qty"] == 4
    assert inv["condition"] == "new"
    assert inv["bin"] == "P-01"
    assert inv["code"] == "CHI-N"

    ident = dms.store.fetchone(
        "SELECT identifier_type, identifier_value FROM part_identifiers WHERE sku = ?",
        ("PILOT-PUMP-01",),
    )
    assert ident is not None
    assert ident["identifier_value"] == "PILOT-OEM-001"


def test_phase9_zero_stock_import(dms_root):
    _, dms = dms_root
    result = commit_transmission_import(ZERO_CSV, dms)
    assert result["committed"] is True
    inv = dms.store.fetchone(
        "SELECT qty FROM inventory_levels WHERE sku = ?",
        ("PILOT-ZERO-01",),
    )
    assert inv is not None
    assert inv["qty"] == 0
    part = dms.store.fetchone(
        "SELECT sku FROM catalog_parts WHERE sku = ?", ("PILOT-ZERO-01",)
    )
    assert part is not None


def test_phase9_invalid_quantity_rejected(dms_root):
    _, dms = dms_root
    before = _counts(dms)
    bad = """sku,name,transmission_family,location,qty
BAD-1,Pump,6L80,CHI-N,-1
"""
    result = preview_transmission_import(bad, dms)
    assert result["ok"] is False
    assert result["invalid_rows"] == 1
    assert _counts(dms) == before

    bad2 = """sku,name,transmission_family,location,qty
BAD-2,Pump,6L80,CHI-N,1.5
"""
    result2 = commit_transmission_import(bad2, dms)
    assert result2["committed"] is False
    assert _counts(dms) == before


def test_phase9_unknown_location_blocked(dms_root):
    _, dms = dms_root
    before = _counts(dms)
    csv_text = """sku,name,transmission_family,location,qty
X-1,Pump,6L80,NOPE-LOC,2
"""
    result = preview_transmission_import(csv_text, dms)
    assert result["ok"] is False
    assert "NOPE-LOC" in result["unknown_locations"]
    assert _counts(dms) == before

    # explicit allow creates on commit
    result2 = commit_transmission_import(
        csv_text, dms, allow_new_locations=True
    )
    assert result2["committed"] is True
    loc = dms.store.fetchone(
        "SELECT code FROM locations WHERE code = ?", ("NOPE-LOC",)
    )
    assert loc is not None


def test_phase9_existing_sku_identity_conflict(seeded):
    _, dms = seeded
    # 6L80-PUMP-01 exists as 6L80
    csv_text = """sku,name,transmission_family,location,qty
6L80-PUMP-01,Totally Different Name,4L60E,CHI-N,9
"""
    before = dms.store.fetchone(
        "SELECT name, transmission_family FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    result = commit_transmission_import(csv_text, dms)
    assert result["committed"] is False
    assert result["invalid_rows"] >= 1
    after = dms.store.fetchone(
        "SELECT name, transmission_family FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    assert after["name"] == before["name"]
    assert after["transmission_family"] == before["transmission_family"]


def test_phase9_duplicate_sku_location_rejected(dms_root):
    _, dms = dms_root
    csv_text = """sku,name,transmission_family,location,qty
DUP-1,Pump A,6L80,CHI-N,1
DUP-1,Pump A,6L80,CHI-N,5
"""
    result = preview_transmission_import(csv_text, dms)
    assert result["ok"] is False
    assert result["invalid_rows"] >= 1
    assert any(
        "duplicate sku/location" in e
        for r in result["rows"]
        for e in r["errors"]
    )


def test_phase9_identical_reimport_idempotent(dms_root):
    _, dms = dms_root
    r1 = commit_transmission_import(VALID_CSV, dms)
    assert r1["committed"] is True
    c1 = _counts(dms)
    r2 = commit_transmission_import(VALID_CSV, dms)
    assert r2["committed"] is True
    c2 = _counts(dms)
    assert c2["catalog"] == c1["catalog"]
    assert c2["inventory"] == c1["inventory"]
    assert c2["identifiers"] == c1["identifiers"]
    # second pass should be updates not inserts
    assert r2["catalog_inserts"] == 0
    assert r2["inventory_inserts"] == 0


def test_phase9_preview_and_commit_same_validation(dms_root):
    _, dms = dms_root
    bad = """sku,name,transmission_family,location,qty
ONLY-NAME-MISSING,,6L80,CHI-N,1
"""
    preview = preview_transmission_import(bad, dms)
    commit = commit_transmission_import(bad, dms)
    assert preview["ok"] is False
    assert commit["committed"] is False
    assert commit["invalid_rows"] == preview["invalid_rows"]


def test_phase9_commit_failure_rolls_back(dms_root, monkeypatch):
    _, dms = dms_root
    before = _counts(dms)
    plan = build_import_plan(VALID_CSV, dms, mode="preview")
    assert plan.invalid_rows == 0

    real_execute = dms.store.execute
    calls = {"n": 0}

    def flaky(sql, params=()):
        calls["n"] += 1
        # fail after some work
        if "INSERT INTO inventory_levels" in str(sql):
            raise RuntimeError("simulated mid-import failure")
        return real_execute(sql, params)

    monkeypatch.setattr(dms.store, "execute", flaky)
    out = commit_import_plan(plan, dms)
    assert out.committed is False
    # restore execute for counting
    monkeypatch.setattr(dms.store, "execute", real_execute)
    # rolled back — no pilot sku
    row = dms.store.fetchone(
        "SELECT sku FROM catalog_parts WHERE sku = ?", ("PILOT-PUMP-01",)
    )
    assert row is None
    assert _counts(dms)["catalog"] == before["catalog"]


def test_phase9_cli_preview_default(dms_root, tmp_path, capsys):
    root, dms = dms_root
    path = tmp_path / "pilot.csv"
    path.write_text(VALID_CSV, encoding="utf-8")
    before = _counts(dms)
    rc = cli_main(["--root", str(root), "transmission-import", str(path)])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "preview"
    assert data["committed"] is False
    assert _counts(dms) == before


def test_phase9_cli_explicit_commit(dms_root, tmp_path, capsys):
    root, dms = dms_root
    path = tmp_path / "pilot.csv"
    path.write_text(VALID_CSV, encoding="utf-8")
    rc = cli_main(
        ["--root", str(root), "transmission-import", str(path), "--commit"]
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "commit"
    assert data["committed"] is True
    row = dms.store.fetchone(
        "SELECT sku FROM catalog_parts WHERE sku = ?", ("PILOT-PUMP-01",)
    )
    assert row is not None


def test_phase9_fresh_root_preview_does_not_initialize_dms(tmp_path: Path):
    """Preview on a never-initialized root must not create DMS files/tables."""
    before = {p.name for p in tmp_path.rglob("*")} if tmp_path.exists() else set()
    dms = DmsService(tmp_path)  # construct only; no ensure_schema
    result = preview_transmission_import(VALID_CSV, dms)
    assert result["ok"] is False
    assert any("not initialized" in e.lower() for e in result["file_errors"])
    assert result["mode"] == "preview"
    assert result["committed"] is False
    # No dms.db created
    assert not (tmp_path / ".parrts" / "dms.db").exists()
    after = {p.name for p in tmp_path.rglob("*")} if any(tmp_path.iterdir()) else set()
    # Allow empty dirs only if something else appeared — dms.db must stay absent
    assert "dms.db" not in after


def test_phase9_existing_verified_sku_stays_verified(seeded):
    _, dms = seeded
    dms.store.execute(
        "UPDATE catalog_parts SET verification_status = ? WHERE sku = ?",
        ("verified", "6L80-PUMP-01"),
    )
    dms.store.commit()
    csv_text = """sku,name,transmission_family,location,qty,condition,bin
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,7,new,A-99
"""
    result = commit_transmission_import(csv_text, dms)
    assert result["committed"] is True
    row = dms.store.fetchone(
        "SELECT verification_status, source FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    assert row["verification_status"] == "verified"
    inv = dms.store.fetchone(
        """
        SELECT i.qty, i.bin FROM inventory_levels i
        JOIN locations l ON l.id = i.location_id
        WHERE i.sku = ? AND l.code = ?
        """,
        ("6L80-PUMP-01", "CHI-N"),
    )
    assert inv["qty"] == 7
    assert inv["bin"] == "A-99"


def test_phase9_existing_source_preserved(seeded):
    _, dms = seeded
    dms.store.execute(
        "UPDATE catalog_parts SET source = ? WHERE sku = ?",
        ("trusted_existing_source", "6L80-PUMP-01"),
    )
    dms.store.commit()
    csv_text = """sku,name,transmission_family,location,qty
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,2
"""
    result = commit_transmission_import(csv_text, dms, source="jp-pilot")
    assert result["committed"] is True
    row = dms.store.fetchone(
        "SELECT source FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    assert row["source"] == "trusted_existing_source"
    assert "pilot_csv" not in str(row["source"])


def test_phase9_existing_category_description_preserved(seeded):
    _, dms = seeded
    dms.store.execute(
        "UPDATE catalog_parts SET category = ?, description = ? WHERE sku = ?",
        ("resolver_category", "original pump description", "6L80-PUMP-01"),
    )
    dms.store.commit()
    csv_text = """sku,name,transmission_family,location,qty,category,description
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,3,other_category,incoming overwrite attempt
"""
    result = commit_transmission_import(csv_text, dms)
    assert result["committed"] is True
    row = dms.store.fetchone(
        "SELECT category, description FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    assert row["category"] == "resolver_category"
    assert row["description"] == "original pump description"


def test_phase9_existing_compatible_sku_catalog_preserved_in_preview(seeded):
    _, dms = seeded
    csv_text = """sku,name,transmission_family,location,qty
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,5
"""
    result = preview_transmission_import(csv_text, dms)
    assert result["ok"] is True
    assert result["catalog_updates"] == 0
    assert result["catalog_inserts"] == 0
    row = result["rows"][0]
    assert row["catalog_action"] == "preserve"
    assert row["existing_sku"] is True
    assert row["inventory_action"] in ("insert", "update")


def test_phase9_new_sku_still_imports_normally(dms_root):
    _, dms = dms_root
    result = commit_transmission_import(VALID_CSV, dms, source="jp-new")
    assert result["committed"] is True
    row = dms.store.fetchone(
        "SELECT source, verification_status, transmission_family FROM catalog_parts "
        "WHERE sku = ?",
        ("PILOT-PUMP-01",),
    )
    assert row["verification_status"] == "unverified"
    assert "pilot_csv" in str(row["source"])
    assert row["transmission_family"] == "6L80"


def test_phase9_existing_sku_new_identifier_without_catalog_rewrite(seeded):
    _, dms = seeded
    before = dms.store.fetchone(
        "SELECT name, source, verification_status, category, description "
        "FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    csv_text = """sku,name,transmission_family,location,qty,identifier_type,identifier_value
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,1,oem,NEW-IDENT-PHASE9
"""
    result = commit_transmission_import(csv_text, dms)
    assert result["committed"] is True
    after = dms.store.fetchone(
        "SELECT name, source, verification_status, category, description "
        "FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    assert dict(after) == dict(before)
    ident = dms.store.fetchone(
        "SELECT identifier_value FROM part_identifiers "
        "WHERE sku = ? AND identifier_value = ?",
        ("6L80-PUMP-01", "NEW-IDENT-PHASE9"),
    )
    assert ident is not None
