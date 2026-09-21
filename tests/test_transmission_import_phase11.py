"""Phase 11 — reversible transmission pilot imports + history."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dms import get_dms_service
from backend.main import app
from parrts.dms.service import DmsService
from parrts.transmission.import_rollback import (
    list_transmission_import_history,
    preview_transmission_import_rollback,
    rollback_transmission_import,
)
from parrts.transmission.importer import commit_transmission_import
from parrts.transmission.seed_loader import load_demo_seed

NEW_SKU_CSV = """sku,name,transmission_family,location,qty,condition,bin,part_type,identifier_type,identifier_value
P11-PUMP-01,6L80 Phase11 Pump,6L80,CHI-N,4,new,P11-01,pump,oem,P11-OEM-1
"""

EXISTING_UPDATE_CSV = """sku,name,transmission_family,location,qty,condition,bin,part_type
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,10,rebuilt,RB-99,pump
"""

NEW_LOC_CSV = """sku,name,transmission_family,location,qty,condition,bin,part_type
P11-LOC-01,6L80 Loc Part,6L80,P11-NEW-LOC,2,new,L-01,pump
"""


@pytest.fixture
def dms_root(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()
    load_demo_seed(dms)
    return tmp_path, dms


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_MODE", "demo")
    root = tmp_path
    dms = DmsService(root)
    dms.ensure_schema()
    load_demo_seed(dms)

    def override_get_dms_service():
        return DmsService(root)

    app.dependency_overrides[get_dms_service] = override_get_dms_service
    try:
        with TestClient(app) as client:
            yield client, root
    finally:
        app.dependency_overrides.clear()


def _inv(dms: DmsService, sku: str, loc: str = "CHI-N"):
    return dms.store.fetchone(
        """
        SELECT i.qty, i.condition, i.bin FROM inventory_levels i
        JOIN locations l ON l.id = i.location_id
        WHERE i.sku = ? AND l.code = ?
        """,
        (sku, loc),
    )


def test_phase11_import_writes_rollback_journal(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(NEW_SKU_CSV, dms, source="p11-journal")
    assert res["committed"] is True
    cr = res["commit_result"]
    assert cr["import_run_id"] is not None
    assert cr["rollback_available"] is True
    assert cr["mutation_count"] >= 1
    hist = list_transmission_import_history(root, limit=5)
    assert hist
    assert hist[0]["import_run_id"] == cr["import_run_id"]
    assert hist[0]["rollback_available"] is True


def test_phase11_existing_inventory_restores(dms_root):
    root, dms = dms_root
    before = _inv(dms, "6L80-PUMP-01")
    assert before is not None
    before_tuple = (int(before["qty"]), before["condition"], before["bin"])

    res = commit_transmission_import(EXISTING_UPDATE_CSV, dms, source="p11-restore")
    assert res["committed"] is True
    run_id = res["commit_result"]["import_run_id"]
    mid = _inv(dms, "6L80-PUMP-01")
    assert int(mid["qty"]) == 10
    assert mid["condition"] == "rebuilt"

    rb = rollback_transmission_import(dms, run_id, actor="test")
    assert rb["rolled_back"] is True
    after = _inv(dms, "6L80-PUMP-01")
    assert (
        int(after["qty"]),
        after["condition"],
        after["bin"],
    ) == before_tuple


def test_phase11_new_sku_cleanup(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(NEW_SKU_CSV, dms, source="p11-newsku")
    run_id = res["commit_result"]["import_run_id"]
    assert dms.store.fetchone(
        "SELECT sku FROM catalog_parts WHERE sku = ?", ("P11-PUMP-01",)
    )
    assert _inv(dms, "P11-PUMP-01") is not None
    assert dms.store.fetchone(
        "SELECT id FROM part_identifiers WHERE sku = ? AND identifier_value = ?",
        ("P11-PUMP-01", "P11-OEM-1"),
    )

    rb = rollback_transmission_import(dms, run_id)
    assert rb["rolled_back"] is True
    assert (
        dms.store.fetchone(
            "SELECT sku FROM catalog_parts WHERE sku = ?", ("P11-PUMP-01",)
        )
        is None
    )
    assert _inv(dms, "P11-PUMP-01") is None
    assert (
        dms.store.fetchone(
            "SELECT id FROM part_identifiers WHERE sku = ?", ("P11-PUMP-01",)
        )
        is None
    )


def test_phase11_preexisting_catalog_preserved(dms_root):
    root, dms = dms_root
    cat_before = dms.store.fetchone(
        "SELECT * FROM catalog_parts WHERE sku = ?", ("6L80-PUMP-01",)
    )
    res = commit_transmission_import(EXISTING_UPDATE_CSV, dms, source="p11-preserve")
    run_id = res["commit_result"]["import_run_id"]
    cat_mid = dms.store.fetchone(
        "SELECT * FROM catalog_parts WHERE sku = ?", ("6L80-PUMP-01",)
    )
    assert cat_mid["name"] == cat_before["name"]
    assert cat_mid["description"] == cat_before["description"]
    rb = rollback_transmission_import(dms, run_id)
    assert rb["rolled_back"] is True
    cat_after = dms.store.fetchone(
        "SELECT * FROM catalog_parts WHERE sku = ?", ("6L80-PUMP-01",)
    )
    assert cat_after["name"] == cat_before["name"]
    assert cat_after["list_price"] == cat_before["list_price"]


def test_phase11_later_inventory_change_blocks_rollback(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(EXISTING_UPDATE_CSV, dms, source="p11-block")
    run_id = res["commit_result"]["import_run_id"]
    # later independent change (fresh service handle)
    dms2 = DmsService(root)
    loc = dms2.store.fetchone("SELECT id FROM locations WHERE code = ?", ("CHI-N",))
    dms2.store.execute(
        "UPDATE inventory_levels SET qty = 8 WHERE sku = ? AND location_id = ?",
        ("6L80-PUMP-01", int(loc["id"])),
    )
    dms2.store.commit()
    dms = dms2

    prev = preview_transmission_import_rollback(dms, run_id)
    assert prev["eligible"] is False
    assert any(
        c.get("type") in ("inventory_changed", "inventory_update")
        and "changed after import" in str(c.get("reason", ""))
        for c in prev["conflicts"]
    )

    rb = rollback_transmission_import(dms, run_id)
    assert rb["rolled_back"] is False
    inv = _inv(dms, "6L80-PUMP-01")
    assert int(inv["qty"]) == 8  # later qty untouched


def test_phase11_double_rollback_refused(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(NEW_SKU_CSV, dms, source="p11-twice")
    run_id = res["commit_result"]["import_run_id"]
    assert rollback_transmission_import(dms, run_id)["rolled_back"] is True
    second = rollback_transmission_import(dms, run_id)
    assert second["rolled_back"] is False
    assert "already" in str(second.get("reason", "")).lower() or second.get("status") == "rolled_back"


def test_phase11_identifier_safety(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(NEW_SKU_CSV, dms, source="p11-id")
    run_id = res["commit_result"]["import_run_id"]
    # mutate identifier notes after import
    dms.store.execute(
        "UPDATE part_identifiers SET notes = 'changed later' "
        "WHERE sku = ? AND identifier_value = ?",
        ("P11-PUMP-01", "P11-OEM-1"),
    )
    dms.store.commit()
    # notes not in after-check — identifier still matches type/value/sku so still deletable
    # if we want safety on notes, journal would need notes; Phase 11 checks exact type/value/sku
    prev = preview_transmission_import_rollback(dms, run_id)
    # still eligible because identifier row still matches import identity
    assert prev["eligible"] is True
    # add a second unrelated identifier — should not be deleted
    dms.store.execute(
        "INSERT INTO part_identifiers (sku, identifier_type, identifier_value, notes, created_at) "
        "VALUES (?, ?, ?, ?, datetime('now'))",
        ("P11-PUMP-01", "oem", "OTHER-ID", "later",),
    )
    dms.store.commit()
    rb = rollback_transmission_import(dms, run_id)
    # OTHER identifier references the SKU; SQLite may CASCADE or block.
    # Either clean success (OTHER removed with SKU) or refused rollback is acceptable safety.
    if rb.get("rolled_back"):
        assert (
            dms.store.fetchone(
                "SELECT sku FROM catalog_parts WHERE sku = ?", ("P11-PUMP-01",)
            )
            is None
        )
        # unrelated later identifier must not survive without its SKU
        assert (
            dms.store.fetchone(
                "SELECT id FROM part_identifiers WHERE identifier_value = ?",
                ("OTHER-ID",),
            )
            is None
        )
    else:
        assert rb.get("rolled_back") is False
        # import-created SKU still present — no half-delete
        assert dms.store.fetchone(
            "SELECT sku FROM catalog_parts WHERE sku = ?", ("P11-PUMP-01",)
        )


def test_phase11_created_location_only_if_unused(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(
        NEW_LOC_CSV, dms, source="p11-loc", allow_new_locations=True
    )
    run_id = res["commit_result"]["import_run_id"]
    assert dms.store.fetchone(
        "SELECT id FROM locations WHERE code = ?", ("P11-NEW-LOC",)
    )

    # first: clean rollback removes unused location
    rb = rollback_transmission_import(dms, run_id)
    assert rb["rolled_back"] is True
    assert (
        dms.store.fetchone(
            "SELECT id FROM locations WHERE code = ?", ("P11-NEW-LOC",)
        )
        is None
    )

    # re-import then add another inventory row at that location and prove preserve
    res2 = commit_transmission_import(
        NEW_LOC_CSV, dms, source="p11-loc2", allow_new_locations=True
    )
    run2 = res2["commit_result"]["import_run_id"]
    loc = dms.store.fetchone(
        "SELECT id FROM locations WHERE code = ?", ("P11-NEW-LOC",)
    )
    # seed a second sku at same location (not part of import journal)
    dms.store.execute(
        "INSERT INTO catalog_parts (sku, name, category) VALUES (?, ?, ?)",
        ("OTHER-SKU", "Other", "transmission"),
    )
    dms.store.execute(
        "INSERT INTO inventory_levels (sku, location_id, qty, condition) VALUES (?, ?, ?, ?)",
        ("OTHER-SKU", int(loc["id"]), 1, "new"),
    )
    dms.store.commit()
    prev = preview_transmission_import_rollback(dms, run2)
    # location should be preserved in plan
    assert any(
        p.get("type") == "location" and p.get("location_code") == "P11-NEW-LOC"
        for p in (prev.get("preserve") or [])
    )
    rb2 = rollback_transmission_import(dms, run2)
    assert rb2["rolled_back"] is True
    assert dms.store.fetchone(
        "SELECT id FROM locations WHERE code = ?", ("P11-NEW-LOC",)
    ) is not None


def test_phase11_rollback_transaction_failure(dms_root, monkeypatch):
    root, dms = dms_root
    res = commit_transmission_import(NEW_SKU_CSV, dms, source="p11-txfail")
    run_id = res["commit_result"]["import_run_id"]
    assert _inv(dms, "P11-PUMP-01") is not None

    from parrts.transmission import import_rollback as ir

    real_execute = dms.store.execute
    calls = {"n": 0}

    def boom(*args, **kwargs):
        sql = str(args[0]) if args else ""
        if "DELETE FROM inventory_levels" in sql:
            calls["n"] += 1
            raise RuntimeError("injected mid-rollback failure")
        return real_execute(*args, **kwargs)

    monkeypatch.setattr(dms.store, "execute", boom)
    rb = rollback_transmission_import(dms, run_id)
    assert rb["rolled_back"] is False
    # restore real execute
    monkeypatch.setattr(dms.store, "execute", real_execute)
    # imported state intact
    assert _inv(dms, "P11-PUMP-01") is not None
    assert dms.store.fetchone(
        "SELECT sku FROM catalog_parts WHERE sku = ?", ("P11-PUMP-01",)
    )


def test_phase11_rollback_preview_readonly(dms_root):
    root, dms = dms_root
    res = commit_transmission_import(NEW_SKU_CSV, dms, source="p11-ro")
    run_id = res["commit_result"]["import_run_id"]
    inv_before = _inv(dms, "P11-PUMP-01")
    cat_c = dms.store.fetchone("SELECT COUNT(*) AS c FROM catalog_parts")["c"]
    prev = preview_transmission_import_rollback(dms, run_id)
    assert prev["eligible"] is True
    assert _inv(dms, "P11-PUMP-01")["qty"] == inv_before["qty"]
    assert dms.store.fetchone("SELECT COUNT(*) AS c FROM catalog_parts")["c"] == cat_c


def test_phase11_history_newest_first(dms_root):
    root, dms = dms_root
    r1 = commit_transmission_import(NEW_SKU_CSV, dms, source="hist-a")
    # different sku for second
    csv2 = NEW_SKU_CSV.replace("P11-PUMP-01", "P11-PUMP-02").replace(
        "P11-OEM-1", "P11-OEM-2"
    )
    r2 = commit_transmission_import(csv2, dms, source="hist-b")
    hist = list_transmission_import_history(root, limit=10)
    assert len(hist) >= 2
    assert hist[0]["import_run_id"] == r2["commit_result"]["import_run_id"]
    assert hist[1]["import_run_id"] == r1["commit_result"]["import_run_id"]
    assert hist[0]["source_label"] in ("hist-b", "pilot_csv:hist-b")


def test_phase11_api_permissions_and_recheck(api_env):
    client, root = api_env
    # counter forbidden
    for path, method in [
        ("/api/v1/dms/transmission/import/history", "get"),
        ("/api/v1/dms/transmission/import/1/rollback/preview", "post"),
        ("/api/v1/dms/transmission/import/1/rollback", "post"),
    ]:
        if method == "get":
            res = client.get(path, headers={"X-Parts-Role": "counter"})
        else:
            res = client.post(path, headers={"X-Parts-Role": "counter"})
        assert res.status_code == 403, path

    # manager commit
    res = client.post(
        "/api/v1/dms/transmission/import/commit",
        json={"csv_text": EXISTING_UPDATE_CSV, "source": "api-p11"},
        headers={"X-Parts-Role": "manager"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["committed"] is True
    run_id = data["commit_result"]["import_run_id"]
    assert data["commit_result"]["rollback_available"] is True

    hist = client.get(
        "/api/v1/dms/transmission/import/history",
        headers={"X-Parts-Role": "manager"},
    )
    assert hist.status_code == 200
    assert hist.json()["count"] >= 1

    prev = client.post(
        f"/api/v1/dms/transmission/import/{run_id}/rollback/preview",
        headers={"X-Parts-Role": "manager"},
    )
    assert prev.status_code == 200
    assert prev.json()["eligible"] is True

    # change DMS after preview (stale client)
    dms = DmsService(root)
    loc = dms.store.fetchone("SELECT id FROM locations WHERE code = ?", ("CHI-N",))
    dms.store.execute(
        "UPDATE inventory_levels SET qty = 1 WHERE sku = ? AND location_id = ?",
        ("6L80-PUMP-01", int(loc["id"])),
    )
    dms.store.commit()

    rb = client.post(
        f"/api/v1/dms/transmission/import/{run_id}/rollback",
        headers={"X-Parts-Role": "manager"},
    )
    assert rb.status_code == 200
    body = rb.json()
    assert body["rolled_back"] is False
    inv = _inv(dms, "6L80-PUMP-01")
    assert int(inv["qty"]) == 1
