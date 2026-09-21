"""Unit-of-work decision layer: RESOLVED vs NEEDS_HUMAN."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from parrts.automation.service import AutomationService
from parrts.dms.service import DmsService
from parrts.transmission.decision import (
    KIND,
    TransmissionEvidence,
    build_unit_of_work,
    evaluate_evidence_policy,
)
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry


@pytest.fixture
def seeded_dms():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        load_demo_seed(dms)
        yield dms


def test_resolved_tahoe_unit_of_work(seeded_dms):
    answer = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", seeded_dms
    )
    assert answer.status == "resolved"
    assert answer.sku == "6L80-PUMP-01"
    assert answer.outcome == "RESOLVED"
    assert answer.confidence is not None and answer.confidence >= 0.75
    assert answer.recommended_action
    assert answer.request_id
    assert answer.decision is not None
    assert answer.decision["evidence"]["sku"] == "6L80-PUMP-01"
    assert answer.evidence_sufficiency == "sufficient"
    assert answer.decision_source == "deterministic_policy"

    runs = AutomationService(seeded_dms.root).list_runs(kind=KIND, limit=10)
    assert runs
    assert runs[0]["detail"].get("outcome") == "RESOLVED"


def test_needs_human_unknown_identifier(seeded_dms):
    answer = answer_transmission_inquiry(
        "Do you have FAKE-IDENT-999?", seeded_dms
    )
    assert answer.status in ("no_match", "insufficient")
    assert answer.outcome == "NEEDS_HUMAN"
    assert answer.ambiguity_reason
    assert answer.recommended_action
    assert "OEM" in (answer.recommended_action or "") or "casting" in (
        answer.recommended_action or ""
    ).lower() or "identifier" in (answer.recommended_action or "").lower()


def test_needs_human_ambiguous_fixture():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        dms.store.execute(
            "INSERT INTO catalog_parts (sku, name, transmission_family, verification_status) "
            "VALUES (?, ?, ?, ?)",
            ("AMBIG-PART-A", "Test Part A", "TEST-FAM", "unverified"),
        )
        dms.store.execute(
            "INSERT INTO catalog_parts (sku, name, transmission_family, verification_status) "
            "VALUES (?, ?, ?, ?)",
            ("AMBIG-PART-B", "Test Part B", "TEST-FAM", "unverified"),
        )
        dms.store.execute(
            "INSERT INTO part_identifiers (sku, identifier_type, identifier_value, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("AMBIG-PART-A", "test", "AMBIG-TEST-001", "2026-01-01"),
        )
        dms.store.execute(
            "INSERT INTO part_identifiers (sku, identifier_type, identifier_value, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("AMBIG-PART-B", "test", "AMBIG-TEST-001", "2026-01-01"),
        )
        dms.store.commit()

        answer = answer_transmission_inquiry("AMBIG-TEST-001", dms)
        assert answer.status == "ambiguous"
        assert answer.outcome == "NEEDS_HUMAN"
        assert answer.sku is None
        assert answer.candidate_match_quality == "ambiguous"
        assert "OEM" in (answer.recommended_action or "") or "casting" in (
            answer.recommended_action or ""
        ).lower()


def test_policy_disputed_escalates():
    evidence = TransmissionEvidence(
        query="6L80 pump",
        deterministic_status="resolved",
        sku="6L80-PUMP-01",
        inventory_available=True,
        aggregate_available=3,
        verification_status="disputed",
        identifiers=[{"identifier_type": "oem", "identifier_value": "x"}],
    )
    d = evaluate_evidence_policy(evidence)
    assert d.outcome == "NEEDS_HUMAN"
    assert "disputed" in (d.ambiguity_reason or "").lower()


def test_build_unit_of_work_from_answer(seeded_dms):
    answer = answer_transmission_inquiry("Do you have 24264418?", seeded_dms)
    uow = build_unit_of_work(answer)
    assert uow.decision.outcome == "RESOLVED"
    assert uow.evidence.sku == "6L80-PUMP-01"
    blob = uow.to_dict()
    assert blob["schema"].startswith("transmission_request_uow")
    assert "human_override" in blob
    assert blob["final_accepted_outcome"] is None
