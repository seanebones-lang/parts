"""Offline API tests for /api/v1/emails (no Postgres)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def email_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Build index for quote path
    from parrts.embeddings import HashingEmbedder
    from parrts.engine import PartsRAGEngine

    eng = PartsRAGEngine(root=tmp_path, embedder=HashingEmbedder())
    eng.build(force_inventory=True)

    monkeypatch.setenv("PARRTS_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTH_MODE", "demo")
    monkeypatch.setenv("ENVIRONMENT", "development")

    import app.api.v1.endpoints.emails as emails_mod
    from app.api.deps import require_user_if_production

    monkeypatch.setattr(emails_mod, "resolve_monorepo_root", lambda: tmp_path)

    app = FastAPI()
    app.include_router(emails_mod.router, prefix="/api/v1/emails", tags=["emails"])
    app.dependency_overrides[require_user_if_production] = lambda: None
    return TestClient(app)


def test_email_seed_list_search_process(email_client: TestClient):
    r = email_client.post("/api/v1/emails/seed", json={"clear": True, "process": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("seeded", 0) >= 6

    s = email_client.get("/api/v1/emails/status")
    assert s.status_code == 200
    st = s.json()
    assert st.get("total", 0) >= 6

    lst = email_client.get("/api/v1/emails/", params={"limit": 50})
    assert lst.status_code == 200
    data = lst.json()
    assert data["count"] >= 6
    assert data["emails"]

    # traffic light present
    colors = {
        (e.get("traffic_light") or {}).get("color")
        if isinstance(e.get("traffic_light"), dict)
        else e.get("traffic_light")
        for e in data["emails"]
    }
    assert colors & {"green", "yellow", "red"}

    sr = email_client.get("/api/v1/emails/search", params={"q": "invoice"})
    assert sr.status_code == 200
    assert sr.json()["count"] >= 1

    eid = data["emails"][0]["id"]
    one = email_client.get(f"/api/v1/emails/{eid}")
    assert one.status_code == 200
    assert one.json()["email"]["id"] == eid

    ing = email_client.post(
        "/api/v1/emails/ingest",
        json={
            "subject": "battery group 51R Honda",
            "body": "Do you have a battery group 51R for Honda?",
            "sender_email": "test@example.com",
            "process": True,
        },
    )
    assert ing.status_code == 200
    assert ing.json()["email"].get("ai_processed") in (True, 1)

    # override + dry-run send
    eid = data["emails"][0]["id"]
    ov = email_client.post(
        f"/api/v1/emails/{eid}/override",
        json={"color": "green", "notes": "ok"},
    )
    assert ov.status_code == 200, ov.text
    sd = email_client.post(f"/api/v1/emails/{eid}/send", json={"dry_run": True})
    assert sd.status_code == 200, sd.text
    assert sd.json()["email"].get("response_sent") in (True, 1)

    mb = email_client.get("/api/v1/emails/mailbox")
    assert mb.status_code == 200
    assert "imap_configured" in mb.json()
