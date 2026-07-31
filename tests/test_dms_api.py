"""DMS API endpoints — offline TestClient (no Postgres).

Skipped when fastapi is not installed so core pytest stays green.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SRC = ROOT / "src"
for p in (ROOT, SRC, BACKEND):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def dms_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolated FastAPI app with DMS router; SQLite under tmp_path."""
    monkeypatch.setenv("PARRTS_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTH_MODE", "demo")

    # Fresh import path so resolve_monorepo_root sees PARRTS_ROOT
    import importlib

    import app.api.v1.endpoints.dms as dms_mod

    importlib.reload(dms_mod)

    # Avoid Postgres via require_user_if_production → get_db
    from app.api.deps import require_user_if_production

    async def _open_demo():
        return None

    app = FastAPI()
    app.include_router(dms_mod.router, prefix="/api/v1/dms")
    app.dependency_overrides[require_user_if_production] = _open_demo

    # Point root resolver at tmp even if env is ignored
    monkeypatch.setattr(dms_mod, "resolve_monorepo_root", lambda: Path(tmp_path))

    with TestClient(app) as client:
        yield client


def test_dms_module_soft_included_in_api_router():
    from app.api.v1.api import router_status

    st = router_status()
    assert "dms" in st["loaded"] or "dms" in st.get("failed", {}), st
    # Prefer loaded; if failed surface reason
    if "dms" in st.get("failed", {}):
        pytest.fail(f"dms failed to load: {st['failed']['dms']}")
    assert st["loaded_count"] >= 15
    assert "dms" in st["loaded"]


def test_dms_status_empty(dms_client: TestClient):
    r = dms_client.get("/api/v1/dms/status")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("success") is True
    assert data.get("ok") is True
    assert data.get("catalog_parts") == 0
    assert "db_path" in data


def test_dms_seed_inventory_catalog(dms_client: TestClient):
    r = dms_client.post("/api/v1/dms/seed", json={"seed": 42, "n_skus": 5, "locations": 3})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    assert body.get("parts_upserted") == 5
    assert body.get("status") == "ok"

    st = dms_client.get("/api/v1/dms/status").json()
    assert st["catalog_parts"] == 5
    assert st["inventory_rows"] == 15

    inv = dms_client.get("/api/v1/dms/inventory").json()
    assert inv["success"] is True
    assert inv["count"] == 15

    cat = dms_client.get("/api/v1/dms/catalog").json()
    assert cat["success"] is True
    assert cat["count"] == 5

    q = dms_client.get("/api/v1/dms/catalog", params={"q": "Brake"}).json()
    assert q["success"] is True
    assert q["count"] >= 1


def test_dms_oem_sync_file(dms_client: TestClient):
    sample = ROOT / "data" / "oem" / "sample_oem_catalog.json"
    if not sample.is_file():
        pytest.skip("sample OEM feed missing")
    r = dms_client.post(
        "/api/v1/dms/oem/sync",
        json={"source": "file", "path": str(sample)},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("parts_upserted") == 15

    inv = dms_client.get("/api/v1/dms/inventory", params={"location": "CHI-N"}).json()
    assert inv["count"] == 15
    skus = {row["sku"] for row in inv["inventory"]}
    assert "OEM-SAMPLE-BP-HC19" in skus


def test_dms_customers_and_orders(dms_client: TestClient):
    assert dms_client.post(
        "/api/v1/dms/seed", json={"seed": 1, "n_skus": 8, "locations": 3}
    ).status_code == 200

    cr = dms_client.post(
        "/api/v1/dms/customers",
        json={
            "name": "API Buyer",
            "email": "buyer@example.com",
            "phone": "555-0199",
            "company": "Demo Shop",
        },
    )
    assert cr.status_code == 200, cr.text
    customer = cr.json()["customer"]
    assert customer["id"] >= 1
    assert customer["name"] == "API Buyer"

    lst = dms_client.get("/api/v1/dms/customers").json()
    assert lst["count"] == 1

    inv = dms_client.get("/api/v1/dms/inventory").json()["inventory"]
    target = next(r for r in inv if int(r["qty"]) >= 2)
    orr = dms_client.post(
        "/api/v1/dms/orders",
        json={
            "customer_id": customer["id"],
            "notes": "api test",
            "lines": [
                {
                    "sku": target["sku"],
                    "location_id": int(target["location_id"]),
                    "qty": 1,
                }
            ],
        },
    )
    assert orr.status_code == 200, orr.text
    order = orr.json()["order"]
    assert order["id"] >= 1
    assert len(order["lines"]) == 1

    orders = dms_client.get("/api/v1/dms/orders").json()
    assert orders["count"] == 1
    assert orders["orders"][0]["lines"][0]["sku"] == target["sku"]


def test_dms_order_insufficient_stock_409(dms_client: TestClient):
    sample = ROOT / "data" / "oem" / "sample_oem_catalog.json"
    if not sample.is_file():
        pytest.skip("sample OEM feed missing")
    assert (
        dms_client.post(
            "/api/v1/dms/oem/sync",
            json={"source": "file", "path": str(sample)},
        ).status_code
        == 200
    )
    cust = dms_client.post(
        "/api/v1/dms/customers", json={"name": "No Stock"}
    ).json()["customer"]
    inv = dms_client.get(
        "/api/v1/dms/inventory", params={"location": "LOGAN"}
    ).json()["inventory"]
    zero = next(r for r in inv if r["sku"] == "OEM-SAMPLE-BR-HC")
    assert int(zero["qty"]) == 0
    bad = dms_client.post(
        "/api/v1/dms/orders",
        json={
            "customer_id": cust["id"],
            "lines": [
                {
                    "sku": "OEM-SAMPLE-BR-HC",
                    "location_id": int(zero["location_id"]),
                    "qty": 1,
                }
            ],
        },
    )
    assert bad.status_code == 409, bad.text


def test_dms_reindex(dms_client: TestClient, tmp_path: Path):
    assert dms_client.post(
        "/api/v1/dms/seed", json={"seed": 7, "n_skus": 4, "locations": 2}
    ).status_code == 200
    r = dms_client.post("/api/v1/dms/reindex", json={"force": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("export_path")
    export = Path(body["export_path"])
    assert export.is_file()
    # inventory.json written under tmp root
    inv_json = tmp_path / ".parrts" / "inventory.json"
    assert inv_json.is_file()


def test_router_status_cli_shape():
    """Task verify: from app.api.v1.api import router_status; print(router_status())."""
    from app.api.v1.api import router_status

    st = router_status()
    assert isinstance(st, dict)
    assert "loaded" in st and "failed" in st
    assert "loaded_count" in st
