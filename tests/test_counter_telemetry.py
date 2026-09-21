"""JP counter pilot telemetry — sessions, lot selection, source isolation, report."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from parrts.dms.service import DmsService
from parrts.transmission.counter_search import counter_search
from parrts.transmission.counter_telemetry import (
    build_pilot_report,
    finalize_session_from_uow_feedback,
    list_sessions,
    record_counter_search_from_result,
    record_lot_selection,
    resolve_telemetry_source,
)
from parrts.transmission.importer import build_import_plan, commit_import_plan
from parrts.transmission.seed_loader import load_demo_seed

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "jp_demo" / "jp_demo_inventory_seed.csv"


@pytest.fixture()
def dms_root(tmp_path: Path):
    if not CSV.is_file():
        pytest.skip("JP demo CSV missing")
    root = tmp_path / "pilot"
    root.mkdir()
    s = DmsService(root)
    s.ensure_schema()
    load_demo_seed(s)
    plan = build_import_plan(
        CSV.read_text(encoding="utf-8"), s, source="jp_demo_inventory", allow_new_locations=False
    )
    assert plan.invalid_rows == 0
    plan = commit_import_plan(plan, s)
    assert plan.committed
    s.store.close()
    return root


@pytest.fixture()
def dms(dms_root: Path):
    s = DmsService(dms_root)
    yield s
    s.store.close()


def test_source_default_is_not_real(monkeypatch):
    monkeypatch.delenv("JP_PILOT_MODE", raising=False)
    monkeypatch.delenv("COUNTER_TELEMETRY_SOURCE", raising=False)
    assert resolve_telemetry_source(None) == "jp_demo"
    monkeypatch.setenv("JP_PILOT_MODE", "real")
    assert resolve_telemetry_source(None) == "jp_real_pilot"
    assert resolve_telemetry_source("test") == "test"
    assert resolve_telemetry_source("jp_demo") == "jp_demo"


def test_record_all_three_modes(dms: DmsService):
    for q, mode in [
        ("6L80-PUMP-01", "exact_match"),
        ("6L80 pump", "inventory_matches"),
        ("6L80 or 6R80 pump which one?", "needs_review"),
    ]:
        r = counter_search(q, dms)
        assert r.search_mode == mode, (q, r.search_mode, r.human_readable)
        tel = record_counter_search_from_result(dms, r, source="test")
        assert tel["ok"] and tel["search_id"]
        row = dms.store.fetchone(
            "SELECT * FROM counter_search_sessions WHERE id = ?",
            (tel["search_id"],),
        )
        assert row is not None
        assert row["search_mode"] == mode
        assert row["source"] == "test"
        if mode == "inventory_matches":
            assert row["proposed_sku"] is None
            assert int(row["candidate_count"]) >= 1
        if mode == "exact_match":
            assert row["proposed_sku"] == "6L80-PUMP-01"
            assert row["request_id"]


def test_idempotent_search_id(dms: DmsService):
    r = counter_search("6L80-PUMP-01", dms)
    a = record_counter_search_from_result(dms, r, source="test", search_id="css_retry_1")
    b = record_counter_search_from_result(dms, r, source="test", search_id="css_retry_1")
    assert a["idempotent"] is False
    assert b["idempotent"] is True
    n = dms.store.fetchone(
        "SELECT COUNT(*) AS n FROM counter_search_sessions WHERE id = 'css_retry_1'"
    )["n"]
    assert int(n) == 1


def test_lot_selection_quote_and_reserve(dms: DmsService):
    r = counter_search("6L80 pump", dms)
    assert r.search_mode == "inventory_matches"
    tel = record_counter_search_from_result(dms, r, source="jp_real_pilot")
    c0 = r.discovery["candidates"][0]
    out = record_lot_selection(
        dms,
        tel["search_id"],
        sku=c0["sku"],
        location=c0["location_code"],
        action="ADD_TO_QUOTE",
        quote_id=42,
    )
    assert out["finalized"] is True
    row = dms.store.fetchone(
        "SELECT * FROM counter_search_sessions WHERE id = ?",
        (tel["search_id"],),
    )
    assert row["selected_sku"] == c0["sku"]
    assert row["selected_action"] == "ADD_TO_QUOTE"
    assert row["finalized_at"]
    assert int(row["quote_id"]) == 42

    r2 = counter_search("4L60E valve body", dms)
    assert r2.search_mode == "inventory_matches"
    tel2 = record_counter_search_from_result(dms, r2, source="jp_real_pilot")
    c1 = r2.discovery["candidates"][0]
    out2 = record_lot_selection(
        dms,
        tel2["search_id"],
        sku=c1["sku"],
        location=c1["location_code"],
        action="RESERVE",
        reservation_id=7,
    )
    assert out2["ok"]
    row2 = dms.store.fetchone(
        "SELECT selected_action, reservation_id FROM counter_search_sessions WHERE id = ?",
        (tel2["search_id"],),
    )
    assert row2["selected_action"] == "RESERVE"
    assert int(row2["reservation_id"]) == 7


def test_selection_rejects_bad_sku_location(dms: DmsService):
    r = counter_search("6L80 pump", dms)
    assert r.search_mode == "inventory_matches"
    tel = record_counter_search_from_result(dms, r, source="test")
    with pytest.raises(ValueError, match="SKU not found"):
        record_lot_selection(
            dms, tel["search_id"], sku="NO-SUCH-SKU", location="CHI-N", action="RESERVE"
        )
    with pytest.raises(ValueError, match="Unknown location|No inventory"):
        record_lot_selection(
            dms,
            tel["search_id"],
            sku="6L80-PUMP-01",
            location="NOPE-LOC",
            action="RESERVE",
        )


def test_inventory_matches_not_resolved(dms: DmsService):
    r = counter_search("6L80 pump", dms)
    assert r.search_mode == "inventory_matches"
    assert r.outcome is None
    tel = record_counter_search_from_result(dms, r, source="test")
    row = dms.store.fetchone(
        "SELECT search_mode, proposed_sku FROM counter_search_sessions WHERE id = ?",
        (tel["search_id"],),
    )
    assert row["search_mode"] == "inventory_matches"
    assert row["proposed_sku"] is None


def test_exact_uow_finalize_linkage(dms: DmsService):
    r = counter_search("6L80-PUMP-01", dms)
    assert r.search_mode == "exact_match" and r.request_id
    tel = record_counter_search_from_result(dms, r, source="jp_real_pilot")
    fin = finalize_session_from_uow_feedback(
        dms, request_id=r.request_id, feedback_action="accept"
    )
    assert fin["updated"] >= 1
    row = dms.store.fetchone(
        "SELECT finalized_at, selected_action FROM counter_search_sessions WHERE id = ?",
        (tel["search_id"],),
    )
    assert row["finalized_at"]
    assert row["selected_action"] == "ACCEPT"


def test_report_excludes_demo_and_counts_finalized_only(dms: DmsService):
    r = counter_search("6L80 pump", dms)
    record_counter_search_from_result(dms, r, source="jp_demo")
    r2 = counter_search("6L80-PUMP-01", dms)
    record_counter_search_from_result(dms, r2, source="jp_real_pilot")
    r3 = counter_search("6R80 pump", dms)
    assert r3.search_mode == "inventory_matches" and r3.discovery
    t3 = record_counter_search_from_result(dms, r3, source="jp_real_pilot")
    c = r3.discovery["candidates"][0]
    record_lot_selection(
        dms, t3["search_id"], sku=c["sku"], location=c["location_code"], action="ADD_TO_QUOTE"
    )

    rep = build_pilot_report(dms, source="jp_real_pilot", target_finalized=50)
    assert rep["total_searches"] == 2
    assert rep["finalized_real_requests"] == 1
    assert rep["progress"].startswith("1 / 50")
    demo_rows = list_sessions(dms, source="jp_demo")
    assert len(demo_rows) == 1
    assert rep["honesty"]["overall_accuracy_not_computed"] is True


def test_api_inquiry_persists_and_selection(dms_root: Path, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "demo")
    monkeypatch.setenv("COUNTER_TELEMETRY_SOURCE", "test")
    monkeypatch.setenv("JEV_DECISION_ENABLED", "0")
    from backend.main import app
    from app.api.v1.endpoints import dms as dms_ep

    def _svc():
        return DmsService(dms_root)

    app.dependency_overrides[dms_ep.get_dms_service] = _svc
    client = TestClient(app)
    try:
        res = client.post(
            "/api/v1/dms/transmission/inquiry",
            json={"query": "6L80 pump", "telemetry_source": "test", "search_id": "css_api_1"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["search_mode"] == "inventory_matches"
        assert body["search_id"] == "css_api_1"
        assert body.get("outcome") is None

        res2 = client.post(
            "/api/v1/dms/transmission/inquiry",
            json={"query": "6L80 pump", "telemetry_source": "test", "search_id": "css_api_1"},
        )
        assert res2.status_code == 200
        s = DmsService(dms_root)
        n = s.store.fetchone(
            "SELECT COUNT(*) AS n FROM counter_search_sessions WHERE id = 'css_api_1'"
        )["n"]
        assert int(n) == 1

        c0 = body["discovery"]["candidates"][0]
        sel = client.post(
            "/api/v1/dms/transmission/counter-search/css_api_1/selection",
            json={
                "sku": c0["sku"],
                "location": c0["location_code"],
                "action": "ADD_TO_QUOTE",
                "quote_id": 9,
            },
        )
        assert sel.status_code == 200, sel.text
        bad = client.post(
            "/api/v1/dms/transmission/counter-search/css_api_1/selection",
            json={"sku": "ZZ-NOPE", "location": "CHI-N", "action": "RESERVE"},
        )
        assert bad.status_code == 400
        s.store.close()
    finally:
        app.dependency_overrides.clear()
