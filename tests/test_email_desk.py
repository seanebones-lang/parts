"""Offline email desk: classify, grade, pipeline, search."""

from __future__ import annotations

from pathlib import Path

import pytest

from parrts.email.classify import classify_email
from parrts.email.policy import grade_email
from parrts.email.service import EmailService
from parrts.embeddings import HashingEmbedder
from parrts.engine import PartsRAGEngine


@pytest.fixture()
def email_root(tmp_path: Path) -> Path:
    # Build a tiny RAG index so quote specialists get real hits
    eng = PartsRAGEngine(root=tmp_path, embedder=HashingEmbedder())
    eng.build(force_inventory=True)
    return tmp_path


def test_classify_quote_and_complaint():
    q = classify_email(
        subject="Quote brake pads 2019 Honda Civic",
        body="How much for front brake pads?",
        sender_email="a@b.com",
    )
    assert q.classification in {"quote_request", "parts_order", "general_inquiry"}
    assert q.specialist in {"parts_quote", "parts_order", "general"}
    assert q.confidence > 0.4

    c = classify_email(
        subject="Unacceptable wrong part",
        body="This is a formal complaint I want a refund now manager",
        sender_email="x@y.com",
    )
    assert c.classification == "complaint"
    assert c.priority == "urgent"
    assert c.specialist == "complaint"


def test_grade_green_yellow_red():
    g = grade_email(
        classification="quote_request",
        class_confidence=0.9,
        priority="medium",
        specialist_ok=True,
        parts_tl_color="green",
        parts_sim=0.8,
        parts_stock=5,
    )
    assert g.color == "green"
    assert g.requires_human is False
    assert g.auto_send_allowed is True

    y = grade_email(
        classification="quote_request",
        class_confidence=0.6,
        priority="medium",
        specialist_ok=True,
        parts_tl_color="yellow",
        parts_sim=0.5,
        parts_stock=2,
    )
    assert y.color == "yellow"
    assert y.requires_human is True

    r = grade_email(
        classification="complaint",
        class_confidence=0.9,
        priority="urgent",
        specialist_ok=True,
    )
    assert r.color == "red"
    assert r.requires_human is True


def test_seed_process_search_list(email_root: Path):
    svc = EmailService(root=email_root)
    out = svc.seed_demo(process=True, clear=True)
    assert out["seeded"] >= 6
    st = svc.status()
    assert st["total"] >= 6
    assert "by_traffic_light" in st
    # Must produce a mix that includes red (complaint)
    colors = set(st["by_traffic_light"].keys())
    assert "red" in colors or any(
        (e.get("traffic_light") or {}).get("color") == "red" for e in svc.list(limit=50)
    )

    rows = svc.list(limit=50)
    assert len(rows) >= 6
    assert all("subject" in r for r in rows)
    # Suggested responses present after process
    processed = [r for r in rows if r.get("ai_processed")]
    assert processed
    assert any(r.get("suggested_response") for r in processed)

    hits = svc.search("brake")
    assert len(hits) >= 1

    one = svc.get(int(rows[0]["id"]))
    assert one is not None
    assert one.get("specialist")


def test_ingest_idempotent_message_id(email_root: Path):
    svc = EmailService(root=email_root)
    a = svc.ingest(
        subject="oil filter Toyota",
        body_text="Need oil filter for 2020 Toyota Camry price please",
        sender_email="z@example.com",
        message_id="idem-1",
        process=True,
    )
    b = svc.ingest(
        subject="oil filter Toyota",
        body_text="Need oil filter for 2020 Toyota Camry price please",
        sender_email="z@example.com",
        message_id="idem-1",
        process=True,
    )
    assert a["id"] == b["id"]
    assert svc.status()["total"] >= 1
