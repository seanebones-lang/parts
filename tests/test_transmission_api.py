"""Phase 4 API tests for transmission inquiry endpoint."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dms import get_dms_service
from backend.main import app
from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed


@pytest.fixture
def api_client():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Prepare the database in the pytest thread.
        setup_dms = DmsService(root)
        setup_dms.ensure_schema()
        load_demo_seed(setup_dms)

        # Important: close the setup connection before TestClient uses the DB.
        setup_dms.store.close()

        # Return a FRESH service for each HTTP request.
        # DmsService construction itself does not open SQLite;
        # the connection will be created when the endpoint accesses it
        # inside the request thread.
        def override_get_dms_service():
            return DmsService(root)

        app.dependency_overrides[get_dms_service] = override_get_dms_service

        try:
            with TestClient(app) as client:
                yield client, root
        finally:
            app.dependency_overrides.clear()


def test_transmission_inquiry_resolved(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={"query": "Do you have a pump for a 2011 Tahoe 6L80?"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "resolved"
    assert data["sku"] == "6L80-PUMP-01"
    assert data["transmission_family"] == "6L80"
    assert data["inventory_available"] is True
    assert data["aggregate_available"] == 3
    assert data["verification_status"] == "unverified"
    assert any(row.get("bin") == "A-01" for row in data["inventory"])


def test_transmission_inquiry_identifier(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={"query": "Do you have 24264418?"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "resolved"
    assert data["sku"] == "6L80-PUMP-01"


def test_transmission_inquiry_sku(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={"query": "Do you have 6L80-PUMP-01?"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "resolved"
    assert data["sku"] == "6L80-PUMP-01"


def test_transmission_inquiry_unknown(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={"query": "Do you have FAKE-IDENT-999?"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("insufficient", "no_match")
    assert data["sku"] is None


def test_transmission_inquiry_ambiguous(api_client):
    client, root = api_client
    dms = DmsService(root)

    dms.store.execute(
        "INSERT INTO catalog_parts "
        "(sku, name, transmission_family, verification_status) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-PART-A", "Test Part A", "TEST-FAM", "unverified"),
    )
    dms.store.execute(
        "INSERT INTO catalog_parts "
        "(sku, name, transmission_family, verification_status) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-PART-B", "Test Part B", "TEST-FAM", "unverified"),
    )

    dms.store.execute(
        "INSERT INTO part_identifiers "
        "(sku, identifier_type, identifier_value, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-PART-A", "test", "AMBIG-API-TEST-001", "2026-01-01"),
    )
    dms.store.execute(
        "INSERT INTO part_identifiers "
        "(sku, identifier_type, identifier_value, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-PART-B", "test", "AMBIG-API-TEST-001", "2026-01-01"),
    )

    dms.store.commit()
    dms.store.close()

    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={"query": "Do you have AMBIG-API-TEST-001?"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ambiguous"
    assert data["sku"] is None


def test_transmission_inquiry_zero_stock(api_client):
    client, root = api_client
    dms = DmsService(root)

    dms.store.execute(
        "INSERT INTO catalog_parts "
        "(sku, name, transmission_family, verification_status) "
        "VALUES (?, ?, ?, ?)",
        (
            "ZERO-STOCK-TEST-01",
            "Zero Stock Test Pump",
            "TEST-FAM",
            "unverified",
        ),
    )

    dms.store.execute(
        "INSERT INTO part_identifiers "
        "(sku, identifier_type, identifier_value, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            "ZERO-STOCK-TEST-01",
            "test",
            "ZERO-STOCK-ID-001",
            "2026-01-01",
        ),
    )

    dms.store.execute(
        "INSERT INTO locations (code, name) VALUES (?, ?)",
        ("TEST-ZERO-LOC", "Test Zero Stock Location"),
    )

    loc_row = dms.store.fetchone(
        "SELECT id FROM locations WHERE code = ?",
        ("TEST-ZERO-LOC",),
    )
    assert loc_row is not None

    dms.store.execute(
        "INSERT INTO inventory_levels "
        "(sku, location_id, qty, condition, bin) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            "ZERO-STOCK-TEST-01",
            loc_row["id"],
            0,
            "new",
            "Z-01",
        ),
    )

    dms.store.commit()
    dms.store.close()
    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={"query": "Do you have ZERO-STOCK-ID-001?"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "resolved"
    assert data["sku"] == "ZERO-STOCK-TEST-01"
    assert data["aggregate_available"] == 0
    assert data["inventory_available"] is False


def test_transmission_inquiry_invalid_request(api_client):
    client, _ = api_client

    response = client.post(
        "/api/v1/dms/transmission/inquiry",
        json={},
    )

    assert response.status_code == 422
