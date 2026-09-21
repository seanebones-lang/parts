"""Phase 10 — transmission pilot import API workflow."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dms import get_dms_service
from backend.main import app
from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed

VALID_CSV = """sku,name,transmission_family,location,qty,condition,bin,part_type,identifier_type,identifier_value
API-PUMP-01,6L80 API Pump Assembly,6L80,CHI-N,3,new,API-01,pump,oem,API-OEM-1
"""


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
            yield client, root, dms
    finally:
        app.dependency_overrides.clear()


def _counts(dms: DmsService) -> dict[str, int]:
    cat = dms.store.fetchone("SELECT COUNT(*) AS c FROM catalog_parts")
    inv = dms.store.fetchone("SELECT COUNT(*) AS c FROM inventory_levels")
    return {
        "catalog": int(cat["c"]) if cat else 0,
        "inventory": int(inv["c"]) if inv else 0,
    }


def test_phase10_preview_valid_no_mutation(api_env):
    client, root, dms = api_env
    before = _counts(dms)
    res = client.post(
        "/api/v1/dms/transmission/import/preview",
        json={"csv_text": VALID_CSV, "source": "jp-api"},
        headers={"X-Parts-Role": "manager"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "preview"
    assert data["ok"] is True
    assert data["valid_rows"] == 1
    assert data["new_sku_count"] == 1
    assert data.get("committed") is False
    # re-open store on same root
    dms2 = DmsService(root)
    assert _counts(dms2) == before


def test_phase10_commit_valid(api_env):
    client, root, _dms = api_env
    res = client.post(
        "/api/v1/dms/transmission/import/commit",
        json={"csv_text": VALID_CSV, "source": "jp-api"},
        headers={"X-Parts-Role": "manager"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "commit"
    assert data["committed"] is True
    dms = DmsService(root)
    row = dms.store.fetchone(
        "SELECT sku, transmission_family FROM catalog_parts WHERE sku = ?",
        ("API-PUMP-01",),
    )
    assert row is not None
    assert row["transmission_family"] == "6L80"
    inv = dms.store.fetchone(
        """
        SELECT i.qty FROM inventory_levels i
        JOIN locations l ON l.id = i.location_id
        WHERE i.sku = ? AND l.code = ?
        """,
        ("API-PUMP-01", "CHI-N"),
    )
    assert inv is not None
    assert inv["qty"] == 3


def test_phase10_invalid_preview(api_env):
    client, root, dms = api_env
    before = _counts(dms)
    bad = """sku,name,transmission_family,location,qty
X,,6L80,CHI-N,-3
"""
    res = client.post(
        "/api/v1/dms/transmission/import/preview",
        json={"csv_text": bad},
        headers={"X-Parts-Role": "manager"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["invalid_rows"] >= 1
    assert _counts(DmsService(root)) == before


def test_phase10_invalid_commit_no_write(api_env):
    client, root, dms = api_env
    before = _counts(dms)
    bad = """sku,name,transmission_family,location,qty
ONLY,,6L80,CHI-N,1
"""
    res = client.post(
        "/api/v1/dms/transmission/import/commit",
        json={"csv_text": bad},
        headers={"X-Parts-Role": "manager"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("committed") is False
    assert _counts(DmsService(root)) == before


def test_phase10_counter_forbidden_preview_and_commit(api_env):
    client, _root, _dms = api_env
    for path in (
        "/api/v1/dms/transmission/import/preview",
        "/api/v1/dms/transmission/import/commit",
    ):
        res = client.post(
            path,
            json={"csv_text": VALID_CSV},
            headers={"X-Parts-Role": "counter"},
        )
        assert res.status_code == 403, path


def test_phase10_manager_and_admin_allowed(api_env):
    client, _root, _dms = api_env
    for role in ("manager", "admin"):
        res = client.post(
            "/api/v1/dms/transmission/import/preview",
            json={"csv_text": VALID_CSV},
            headers={"X-Parts-Role": role},
        )
        assert res.status_code == 200, role
        assert res.json()["mode"] == "preview"


def test_phase10_existing_sku_preservation_via_api(api_env):
    client, root, dms = api_env
    dms.store.execute(
        "UPDATE catalog_parts SET verification_status = ?, source = ? WHERE sku = ?",
        ("verified", "trusted_existing_source", "6L80-PUMP-01"),
    )
    dms.store.commit()
    csv_text = """sku,name,transmission_family,location,qty,condition,bin
6L80-PUMP-01,6L80 Transmission Pump Assembly,6L80,CHI-N,8,new,B-22
"""
    res = client.post(
        "/api/v1/dms/transmission/import/commit",
        json={"csv_text": csv_text, "source": "jp-overwrite-attempt"},
        headers={"X-Parts-Role": "manager"},
    )
    assert res.status_code == 200
    assert res.json()["committed"] is True
    dms2 = DmsService(root)
    row = dms2.store.fetchone(
        "SELECT verification_status, source FROM catalog_parts WHERE sku = ?",
        ("6L80-PUMP-01",),
    )
    assert row["verification_status"] == "verified"
    assert row["source"] == "trusted_existing_source"
    inv = dms2.store.fetchone(
        """
        SELECT i.qty, i.bin FROM inventory_levels i
        JOIN locations l ON l.id = i.location_id
        WHERE i.sku = ? AND l.code = ?
        """,
        ("6L80-PUMP-01", "CHI-N"),
    )
    assert inv["qty"] == 8
    assert inv["bin"] == "B-22"


def test_phase10_unknown_location_default_and_allow(api_env):
    client, root, dms = api_env
    before = _counts(dms)
    csv_text = """sku,name,transmission_family,location,qty
LOC-NEW-1,Pump,6L80,BRAND-NEW-LOC,2
"""
    blocked = client.post(
        "/api/v1/dms/transmission/import/commit",
        json={"csv_text": csv_text, "allow_new_locations": False},
        headers={"X-Parts-Role": "manager"},
    )
    assert blocked.status_code == 200
    assert blocked.json().get("committed") is False
    assert _counts(DmsService(root)) == before

    allowed = client.post(
        "/api/v1/dms/transmission/import/commit",
        json={"csv_text": csv_text, "allow_new_locations": True},
        headers={"X-Parts-Role": "manager"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["committed"] is True
    loc = DmsService(root).store.fetchone(
        "SELECT code FROM locations WHERE code = ?",
        ("BRAND-NEW-LOC",),
    )
    assert loc is not None
