"""Phase 4 API tests for transmission inquiry endpoint."""
from fastapi.testclient import TestClient
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed


client = TestClient(app)


def test_transmission_inquiry_resolved():
    response = client.post("/api/v1/dms/transmission/inquiry", json={
        "query": "Do you have a pump for a 2011 Tahoe 6L80?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["sku"] == "6L80-PUMP-01"
    assert data["inventory_available"] is True
    assert data["aggregate_available"] == 3


def test_transmission_inquiry_identifier():
    response = client.post("/api/v1/dms/transmission/inquiry", json={
        "query": "Do you have 24264418?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["sku"] == "6L80-PUMP-01"


def test_transmission_inquiry_unknown():
    response = client.post("/api/v1/dms/transmission/inquiry", json={
        "query": "Do you have FAKE-IDENT-999?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("insufficient", "no_match")
    assert data["sku"] is None


def test_transmission_inquiry_invalid_request():
    response = client.post("/api/v1/dms/transmission/inquiry", json={})
    assert response.status_code == 422  # FastAPI validation error