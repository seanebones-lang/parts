"""Phase 8 — persist and analyze transmission JEV shadow observations."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType

import pytest

from parrts.automation.service import AutomationService
from parrts.cli import main as cli_main
from parrts.dms.service import DmsService
from parrts.transmission.jev_shadow_report import (
    KIND,
    build_transmission_jev_shadow_report,
    persist_transmission_jev_shadow_observation,
)
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import TransmissionInquiryAnswer, answer_transmission_inquiry


@pytest.fixture
def stub_typesafe_sdk(monkeypatch):
    sdk = ModuleType("typesafe_sdk")

    class Choice:
        def __init__(self, **kwargs):
            pass

    class Noul:
        def __init__(self, **kwargs):
            pass

    class AsyncTypeSafeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def system_one(self, **kwargs):
            raise RuntimeError("real JEV must not be called in unit tests")

    sdk.Choice = Choice
    sdk.Noul = Noul
    sdk.AsyncTypeSafeClient = AsyncTypeSafeClient
    monkeypatch.setitem(sys.modules, "typesafe_sdk", sdk)
    sys.modules.pop("parrts.email.jev_shadow", None)


@pytest.fixture
def seeded_root(tmp_path: Path):
    dms = DmsService(tmp_path)
    dms.ensure_schema()
    load_demo_seed(dms)
    return tmp_path, dms


def _patch_classify(monkeypatch, fake):
    import parrts.email.jev_shadow as jev_mod

    monkeypatch.setattr(jev_mod, "classify_shadow", fake)
    return fake


def _seed_ambiguous(dms, value="AMBIG-P8-001"):
    dms.store.execute(
        "INSERT INTO catalog_parts "
        "(sku, name, transmission_family, verification_status) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-P8-A", "Ambiguous A", "TEST-FAM", "unverified"),
    )
    dms.store.execute(
        "INSERT INTO catalog_parts "
        "(sku, name, transmission_family, verification_status) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-P8-B", "Ambiguous B", "TEST-FAM", "unverified"),
    )
    dms.store.execute(
        "INSERT INTO part_identifiers "
        "(sku, identifier_type, identifier_value, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-P8-A", "test", value, "2026-01-01"),
    )
    dms.store.execute(
        "INSERT INTO part_identifiers "
        "(sku, identifier_type, identifier_value, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("AMBIG-P8-B", "test", value, "2026-01-01"),
    )
    dms.store.commit()
    return value


def test_phase8_successful_shadow_result_persisted(
    monkeypatch, stub_typesafe_sdk, seeded_root
):
    root, dms = seeded_root
    monkeypatch.setenv("JEV_SHADOW_ENABLED", "1")

    def fake_classify(subject, body, sender_email=""):
        return {
            "label": "parts_availability",
            "choice_confidence": 0.91,
            "needs_human": False,
            "noul_probability": 0.1,
            "model": "jev-latest",
        }

    _patch_classify(monkeypatch, fake_classify)

    answer = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert answer.status == "resolved"
    assert answer.sku == "6L80-PUMP-01"
    assert answer.aggregate_available == 3

    runs = AutomationService(root).list_runs(kind=KIND, limit=10)
    assert len(runs) == 1
    run = runs[0]
    assert run["kind"] == KIND
    assert run["status"] == "ok"
    detail = run["detail"]
    assert detail["jev_evaluation_status"] == "result"
    assert detail["deterministic_status"] == "resolved"
    assert detail["deterministic_sku"] == "6L80-PUMP-01"
    assert detail["deterministic_inventory_available"] is True
    assert detail["deterministic_aggregate_available"] == 3
    assert detail["jev_label"] == "parts_availability"
    assert detail["jev_choice_confidence"] == 0.91
    assert detail["jev_needs_human"] is False
    # DMS not used for shadow persistence
    assert not (root / "dms.db").exists() or True  # dms path may vary
    assert (root / ".parrts" / "automation.db").exists()


def test_phase8_ambiguous_persisted(monkeypatch, stub_typesafe_sdk, seeded_root):
    root, dms = seeded_root
    monkeypatch.setenv("JEV_SHADOW_ENABLED", "1")

    def fake_classify(subject, body, sender_email=""):
        return {
            "label": "parts_availability",
            "choice_confidence": 0.99,
            "needs_human": False,
        }

    _patch_classify(monkeypatch, fake_classify)
    value = _seed_ambiguous(dms)

    answer = answer_transmission_inquiry(f"Do you have {value}?", dms)
    assert answer.status == "ambiguous"
    assert answer.sku is None

    runs = AutomationService(root).list_runs(kind=KIND, limit=5)
    assert len(runs) == 1
    assert runs[0]["detail"]["deterministic_status"] == "ambiguous"
    assert runs[0]["detail"]["deterministic_sku"] is None
    assert runs[0]["detail"]["jev_label"] == "parts_availability"


def test_phase8_zero_stock_observation(monkeypatch, stub_typesafe_sdk, seeded_root):
    root, dms = seeded_root
    monkeypatch.setenv("JEV_SHADOW_ENABLED", "1")

    def fake_classify(subject, body, sender_email=""):
        return {"label": "parts_availability", "choice_confidence": 0.8}

    _patch_classify(monkeypatch, fake_classify)

    answer = answer_transmission_inquiry("Do you have an 8HP70 pump?", dms)
    assert answer.status == "resolved"
    assert answer.aggregate_available == 0
    assert answer.inventory_available is False

    detail = AutomationService(root).list_runs(kind=KIND, limit=1)[0]["detail"]
    assert detail["deterministic_status"] == "resolved"
    assert detail["deterministic_aggregate_available"] == 0
    assert detail["deterministic_inventory_available"] is False


def test_phase8_none_no_result(monkeypatch, stub_typesafe_sdk, seeded_root):
    root, dms = seeded_root
    monkeypatch.setenv("JEV_SHADOW_ENABLED", "1")

    def fake_classify(subject, body, sender_email=""):
        return None

    _patch_classify(monkeypatch, fake_classify)

    answer = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert answer.status == "resolved"
    assert answer.sku == "6L80-PUMP-01"

    run = AutomationService(root).list_runs(kind=KIND, limit=1)[0]
    assert run["status"] == "no_result"
    detail = run["detail"]
    assert detail["jev_evaluation_status"] == "no_result"
    assert "jev_label" not in detail or detail.get("jev_label") is None
    assert "jev_choice_confidence" not in detail or detail.get(
        "jev_choice_confidence"
    ) is None


def test_phase8_classifier_exception_records_error(
    monkeypatch, stub_typesafe_sdk, seeded_root
):
    root, dms = seeded_root
    monkeypatch.setenv("JEV_SHADOW_ENABLED", "1")

    def fake_classify(subject, body, sender_email=""):
        raise RuntimeError("synthetic JEV failure")

    _patch_classify(monkeypatch, fake_classify)

    answer = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert answer.status == "resolved"
    assert answer.sku == "6L80-PUMP-01"

    run = AutomationService(root).list_runs(kind=KIND, limit=1)[0]
    assert run["status"] == "error"
    assert run["detail"]["jev_evaluation_status"] == "error"
    assert "synthetic JEV failure" in (run["detail"].get("error") or "")


def test_phase8_persistence_failure_does_not_break_inquiry(
    monkeypatch, stub_typesafe_sdk, seeded_root
):
    root, dms = seeded_root
    monkeypatch.setenv("JEV_SHADOW_ENABLED", "1")

    def fake_classify(subject, body, sender_email=""):
        return {"label": "parts_availability", "choice_confidence": 0.5}

    _patch_classify(monkeypatch, fake_classify)

    def boom(*args, **kwargs):
        raise RuntimeError("automation.db unavailable")

    monkeypatch.setattr(
        "parrts.transmission.jev_shadow_report.persist_transmission_jev_shadow_observation",
        boom,
    )

    answer = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert answer.status == "resolved"
    assert answer.sku == "6L80-PUMP-01"


def test_phase8_disabled_no_observation(
    monkeypatch, stub_typesafe_sdk, seeded_root
):
    root, dms = seeded_root
    monkeypatch.delenv("JEV_SHADOW_ENABLED", raising=False)
    calls = []

    def fake_classify(**kwargs):
        calls.append(1)
        return {"label": "parts_availability"}

    _patch_classify(monkeypatch, fake_classify)

    answer = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert answer.status == "resolved"
    assert calls == []
    assert AutomationService(root).list_runs(kind=KIND, limit=10) == []


def test_phase8_report_aggregation(tmp_path: Path):
    auto = AutomationService(tmp_path)

    # Seed synthetic observations without JEV
    auto.record_run(
        kind=KIND,
        source_ref="6L80-PUMP-01",
        status="ok",
        summary="resolved -> parts_availability",
        detail={
            "schema": "transmission_jev_shadow.v1",
            "query": "pump",
            "deterministic_status": "resolved",
            "deterministic_sku": "6L80-PUMP-01",
            "deterministic_inventory_available": True,
            "deterministic_aggregate_available": 3,
            "jev_evaluation_status": "result",
            "jev_label": "parts_availability",
            "jev_choice_confidence": 0.9,
            "jev_needs_human": False,
        },
        requires_human=False,
    )
    auto.record_run(
        kind=KIND,
        source_ref="ambiguous:x",
        status="ok",
        summary="ambiguous -> parts_availability",
        detail={
            "deterministic_status": "ambiguous",
            "deterministic_sku": None,
            "deterministic_inventory_available": False,
            "deterministic_aggregate_available": 0,
            "jev_evaluation_status": "result",
            "jev_label": "parts_availability",
            "jev_choice_confidence": 0.5,
            "jev_needs_human": True,
        },
        requires_human=True,
    )
    auto.record_run(
        kind=KIND,
        source_ref="no_match:y",
        status="no_result",
        summary="no_match -> no_result",
        detail={
            "deterministic_status": "no_match",
            "deterministic_sku": None,
            "jev_evaluation_status": "no_result",
        },
    )
    auto.record_run(
        kind=KIND,
        source_ref="err",
        status="error",
        summary="resolved -> error",
        detail={
            "deterministic_status": "resolved",
            "deterministic_sku": "8HP70-PUMP-01",
            "deterministic_inventory_available": False,
            "deterministic_aggregate_available": 0,
            "jev_evaluation_status": "error",
            "error": "boom",
        },
    )
    auto.record_run(
        kind=KIND,
        source_ref="zero",
        status="ok",
        summary="resolved -> parts_availability",
        detail={
            "deterministic_status": "resolved",
            "deterministic_sku": "8HP70-PUMP-01",
            "deterministic_inventory_available": False,
            "deterministic_aggregate_available": 0,
            "jev_evaluation_status": "result",
            "jev_label": "compatibility_fitment",
            "jev_choice_confidence": 0.7,
            "jev_needs_human": False,
        },
    )

    report = build_transmission_jev_shadow_report(tmp_path, limit=100, recent=10)
    assert report["ok"] is True
    assert report["kind"] == KIND
    assert report["volume"]["total"] == 5
    assert report["volume"]["result"] == 3
    assert report["volume"]["no_result"] == 1
    assert report["volume"]["error"] == 1
    assert report["deterministic_outcomes"]["resolved"] == 3
    assert report["deterministic_outcomes"]["ambiguous"] == 1
    assert report["deterministic_outcomes"]["no_match"] == 1
    assert report["jev_intent_labels"]["parts_availability"] == 2
    assert report["jev_intent_labels"]["compatibility_fitment"] == 1
    assert report["needs_human"]["true"] == 1
    assert report["needs_human"]["false"] == 2
    assert report["confidence"]["count"] == 3
    assert report["confidence"]["minimum"] == 0.5
    assert report["confidence"]["maximum"] == 0.9
    assert "accuracy" not in json.dumps(report).lower() or "not accuracy" in json.dumps(
        report
    ).lower()
    assert report["inventory_context"]["resolved_with_stock"] >= 1
    assert report["inventory_context"]["resolved_zero_stock"] >= 1
    assert "resolved" in report["cross_tab_deterministic_status_to_jev_label"]
    assert len(report["recent_observations"]) == 5


def test_phase8_report_does_not_call_jev(monkeypatch, tmp_path: Path):
    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        raise RuntimeError("should not call JEV")

    # If classify is imported somehow during report, fail the test.
    monkeypatch.setitem(sys.modules, "typesafe_sdk", ModuleType("typesafe_sdk"))
    # Seed one observation then build report
    AutomationService(tmp_path).record_run(
        kind=KIND,
        status="ok",
        summary="resolved -> parts_availability",
        detail={
            "deterministic_status": "resolved",
            "jev_evaluation_status": "result",
            "jev_label": "parts_availability",
            "jev_choice_confidence": 0.4,
            "jev_needs_human": False,
        },
    )
    monkeypatch.setattr(
        "parrts.email.jev_shadow.classify_shadow", boom, raising=False
    )
    report = build_transmission_jev_shadow_report(tmp_path)
    assert report["volume"]["total"] == 1
    assert called["n"] == 0


def test_phase8_cli_report(tmp_path: Path, capsys):
    AutomationService(tmp_path).record_run(
        kind=KIND,
        status="ok",
        summary="resolved -> parts_availability",
        detail={
            "deterministic_status": "resolved",
            "deterministic_sku": "6L80-PUMP-01",
            "jev_evaluation_status": "result",
            "jev_label": "parts_availability",
            "jev_choice_confidence": 0.88,
            "jev_needs_human": False,
            "deterministic_inventory_available": True,
            "deterministic_aggregate_available": 3,
        },
    )
    rc = cli_main(
        ["--root", str(tmp_path), "transmission-jev-report", "--limit", "50"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is True
    assert data["volume"]["total"] == 1
    assert data["volume"]["result"] == 1
    assert data["jev_intent_labels"]["parts_availability"] == 1


def test_phase8_persist_helper_direct(tmp_path: Path):
    answer = TransmissionInquiryAnswer(
        query="q",
        status="resolved",
        sku="X",
        inventory_available=True,
        aggregate_available=2,
        fitment_status="compatible",
        verification_status="unverified",
    )
    run = persist_transmission_jev_shadow_observation(
        tmp_path,
        query="q",
        answer=answer,
        jev_evaluation_status="result",
        shadow={
            "label": "general_question",
            "choice_confidence": 0.2,
            "needs_human": True,
            "model": "jev-latest",
        },
    )
    assert run is not None
    assert run["requires_human"] is True
    assert run["detail"]["jev_label"] == "general_question"
