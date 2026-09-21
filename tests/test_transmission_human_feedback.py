"""Human feedback loop on transmission_request_uow records."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dms import get_dms_service
from backend.main import app
from parrts.automation.service import AutomationService
from parrts.dms.service import DmsService
from parrts.transmission.decision import (
    KIND,
    apply_human_feedback,
    find_unit_of_work_run,
)
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry


@pytest.fixture
def seeded_root():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dms = DmsService(root)
        dms.ensure_schema()
        load_demo_seed(dms)
        yield root


def test_accept_resolved_unchanged(seeded_root):
    dms = DmsService(seeded_root)
    ans = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert ans.outcome == "RESOLVED"
    assert ans.request_id
    rid = ans.request_id

    out = apply_human_feedback(
        seeded_root, rid, action="accept", actor="test"
    )
    assert out["ok"] is True
    assert out["human_override"] is False
    assert out["final_accepted_outcome"] == "RESOLVED"
    assert out["final_accepted_sku"] == "6L80-PUMP-01"
    assert out["final_result_recorded"] is True
    assert out["system_sku"] == "6L80-PUMP-01"
    assert out["system_outcome"] == "RESOLVED"

    run = find_unit_of_work_run(seeded_root, rid)
    assert run is not None
    d = run["detail"]
    assert d["final_result_recorded"] is True
    assert d["human_override"] is False
    assert d["system_sku"] == "6L80-PUMP-01"
    assert d["final_accepted_sku"] == "6L80-PUMP-01"
    assert d["request_id"] == rid


def test_correct_resolved_override(seeded_root):
    dms = DmsService(seeded_root)
    ans = answer_transmission_inquiry("Do you have 24264418?", dms)
    assert ans.outcome == "RESOLVED"
    rid = ans.request_id
    system_sku = ans.sku

    out = apply_human_feedback(
        seeded_root,
        rid,
        action="correct",
        final_sku="6L80-VB-01",
        note="counter chose valve body",
        actor="test",
    )
    assert out["ok"] is True
    assert out["human_override"] is True
    assert out["final_accepted_sku"] == "6L80-VB-01"
    assert out["system_sku"] == system_sku
    assert out["system_outcome"] == "RESOLVED"
    # original system decision retained
    d = find_unit_of_work_run(seeded_root, rid)["detail"]
    assert d["system_sku"] == system_sku
    assert d["original_system_sku"] == system_sku
    assert d["final_accepted_sku"] == "6L80-VB-01"
    assert d["final_accepted_note"] == "counter chose valve body"


def test_needs_human_manual_resolve(seeded_root):
    dms = DmsService(seeded_root)
    ans = answer_transmission_inquiry("Do you have FAKE-IDENT-999?", dms)
    assert ans.outcome == "NEEDS_HUMAN"
    rid = ans.request_id

    # cannot accept
    bad = apply_human_feedback(seeded_root, rid, action="accept")
    assert bad["ok"] is False

    out = apply_human_feedback(
        seeded_root,
        rid,
        action="resolve",
        final_sku="6L80-PUMP-01",
        note="counter identified pump",
    )
    assert out["ok"] is True
    assert out["human_override"] is True
    assert out["final_accepted_outcome"] == "RESOLVED"
    assert out["final_accepted_sku"] == "6L80-PUMP-01"
    assert out["system_outcome"] == "NEEDS_HUMAN"
    d = find_unit_of_work_run(seeded_root, rid)["detail"]
    assert d["system_outcome"] == "NEEDS_HUMAN"
    assert d["final_accepted_sku"] == "6L80-PUMP-01"


def test_invalid_request_id_no_mutation(seeded_root):
    dms = DmsService(seeded_root)
    ans = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    before = AutomationService(seeded_root).list_runs(kind=KIND, limit=20)
    before_detail = dict(before[0]["detail"])

    out = apply_human_feedback(
        seeded_root,
        "00000000-0000-0000-0000-000000000000",
        action="accept",
    )
    assert out["ok"] is False
    assert "not found" in str(out.get("error", "")).lower()

    after = AutomationService(seeded_root).list_runs(kind=KIND, limit=20)
    assert after[0]["detail"] == before_detail
    assert after[0]["detail"]["request_id"] == ans.request_id
    assert after[0]["detail"].get("final_result_recorded") is False


def test_feedback_api_accept(seeded_root, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "demo")
    root = seeded_root

    def override():
        return DmsService(root)

    app.dependency_overrides[get_dms_service] = override
    try:
        with TestClient(app) as client:
            inq = client.post(
                "/api/v1/dms/transmission/inquiry",
                json={"query": "Do you have 6L80-PUMP-01?"},
            )
            assert inq.status_code == 200
            data = inq.json()
            assert data["outcome"] == "RESOLVED"
            rid = data["request_id"]

            fb = client.post(
                "/api/v1/dms/transmission/inquiry/feedback",
                json={"request_id": rid, "action": "accept"},
            )
            assert fb.status_code == 200
            body = fb.json()
            assert body["final_result_recorded"] is True
            assert body["human_override"] is False
            assert body["final_accepted_sku"] == data["sku"]

            missing = client.post(
                "/api/v1/dms/transmission/inquiry/feedback",
                json={
                    "request_id": "11111111-1111-1111-1111-111111111111",
                    "action": "accept",
                },
            )
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
