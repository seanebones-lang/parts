"""Transmission email desk uses DMS + counter_search — never legacy Chicago RAG."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from parrts.dms.service import DmsService
from parrts.email.seed_data import TRANSMISSION_DEMO_EMAILS
from parrts.email.service import EmailService
from parrts.email.specialists import PartsQuoteSpecialist, _build_query
from parrts.email.transmission_parts import TransmissionPartsAdapter
from parrts.email.vertical import resolve_parrts_vertical
from parrts.transmission.importer import build_import_plan, commit_import_plan
from parrts.transmission.seed_loader import load_demo_seed

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "jp_demo" / "jp_demo_inventory_seed.csv"

LEGACY_LEAK_PATTERNS = [
    r"Honda\s+Civic",
    r"Toyota\s+Camry",
    r"Ford\s+F-150\s+brake",
    r"Brake\s+Pads",
    r"Brake\s+Rotors",
    r"Oil\s+Filter",
    r"Loop\s+Luxury\s+Autos",
    r"Logan\s+Square\s+Motors",
    r"Chicago\s+North",
    r"Wrigley\s+Dealership",
    r"South\s+Side\s+Parts",
    r"West\s+Town\s+Wheels",
    r"O'Hare\s+Auto",
]


def _blob(*parts: object) -> str:
    return "\n".join(str(p or "") for p in parts)


def _assert_no_legacy_leak(text: str, *, context: str = "") -> None:
    low = text or ""
    for pat in LEGACY_LEAK_PATTERNS:
        assert not re.search(pat, low, flags=re.I), f"legacy leak {pat!r} in {context}: {low[:400]}"


@pytest.fixture()
def tx_root(tmp_path: Path, monkeypatch):
    if not CSV.is_file():
        pytest.skip("JP demo CSV missing")
    monkeypatch.setenv("PARRTS_VERTICAL", "transmission")
    monkeypatch.delenv("EMAIL_VERTICAL", raising=False)
    root = tmp_path / "tx_email"
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


def test_vertical_resolve(monkeypatch):
    monkeypatch.delenv("PARRTS_VERTICAL", raising=False)
    monkeypatch.delenv("EMAIL_VERTICAL", raising=False)
    assert resolve_parrts_vertical(None) == "generic"
    assert resolve_parrts_vertical("transmission") == "transmission"
    monkeypatch.setenv("PARRTS_VERTICAL", "jp")
    assert resolve_parrts_vertical(None) == "transmission"


def test_adapter_never_parts_rag(tx_root: Path):
    ad = TransmissionPartsAdapter(tx_root)
    ad.ensure_ready()
    assert ad.is_transmission_adapter is True
    r = ad.query("6L80 pump")
    d = r.to_dict()
    assert d["inventory_source"] == "transmission_dms"
    assert d["search_mode"] in ("inventory_matches", "exact_match", "needs_review")
    _assert_no_legacy_leak(_blob(d.get("answer"), json.dumps(d.get("hits"))), context="6L80 pump")


def test_6l80_pump_quote_email(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    assert svc.vertical == "transmission"
    assert getattr(svc._get_engine(), "is_transmission_adapter", False)
    row = svc.ingest(
        subject="Need price on a 6L80 pump for a 2011 Tahoe",
        body_text="Counter request: 6L80 pump availability for 2011 Tahoe.",
        sender_email="shop@example.com",
        process=True,
    )
    draft = row.get("suggested_response") or ""
    hits = row.get("hits") or []
    _assert_no_legacy_leak(_blob(draft, json.dumps(hits), row.get("traffic_reason")), context="pump")
    # transmission-only SKUs if any
    for h in hits:
        sku = str((h.get("part") or h).get("sku") or h.get("sku") or "")
        if sku:
            assert "BRAKE" not in sku.upper()
            assert "CIVIC" not in sku.upper()


def test_6r80_valve_body_email(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    row = svc.ingest(
        subject="Do you have a rebuilt 6R80 valve body?",
        body_text="Looking for a rebuilt 6R80 valve body.",
        sender_email="a@b.com",
        process=True,
    )
    _assert_no_legacy_leak(
        _blob(row.get("suggested_response"), json.dumps(row.get("hits") or [])),
        context="6r80 vb",
    )


def test_10r80_reaction_drum_no_brakes(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    row = svc.ingest(
        subject="Need 10R80 reaction drum ASAP — place order",
        body_text=(
            "Please place an order for a 10R80 reaction drum ASAP. "
            "Qty 1. Ship overnight if not on the shelf. PO: PS-4412."
        ),
        sender_email="buyer@precisionshift.example",
        process=True,
    )
    draft = row.get("suggested_response") or ""
    hits = row.get("hits") or []
    blob = _blob(draft, json.dumps(hits), row.get("traffic_reason"), row.get("traffic_light"))
    _assert_no_legacy_leak(blob, context="10R80 drum")
    assert "Honda" not in draft
    assert "Civic" not in draft
    assert "brake" not in draft.lower()
    # must not invent fake drum SKU from generic catalog
    for h in hits:
        name = str((h.get("part") or h).get("name") or h.get("name") or "").lower()
        assert "brake" not in name
        assert "civic" not in name


def test_oem_24264418_exact(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    row = svc.ingest(
        subject="Do you have OEM 24264418?",
        body_text="Do you have OEM 24264418 in stock?",
        sender_email="tech@h.example",
        process=True,
    )
    draft = (row.get("suggested_response") or "").upper()
    hits = row.get("hits") or []
    skus = [str((h.get("part") or h).get("sku") or h.get("sku") or "") for h in hits]
    assert "6L80-PUMP-01" in draft or "6L80-PUMP-01" in skus
    _assert_no_legacy_leak(_blob(row.get("suggested_response"), json.dumps(hits)))


def test_substitution_and_ambiguous_need_review(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    for subj, body in [
        (
            "Can I use a 6L90 pump instead of a 6L80?",
            "Customer asking: can I use a 6L90 pump instead of a 6L80?",
        ),
        (
            "Need a pump — not sure 6L80 or 6L90",
            "Need a pump — customer said 6L80 or maybe 6L90.",
        ),
    ]:
        row = svc.ingest(subject=subj, body_text=body, sender_email="x@y.com", process=True)
        draft = row.get("suggested_response") or ""
        hits = row.get("hits") or []
        _assert_no_legacy_leak(_blob(draft, json.dumps(hits)), context=subj)
        # should not confidently pick one wrong SKU as sole answer without review language
        assert "need" in draft.lower() or "confirm" in draft.lower() or "information" in draft.lower() or hits == []


def test_complaint_red_no_generic_lookup(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    row = svc.ingest(
        subject="Customer says wrong valve body was shipped — need replacement",
        body_text="Formal complaint: wrong valve body shipped. Need replacement 6L80 valve body.",
        sender_email="ops@allied.example",
        process=True,
    )
    color = row.get("traffic_light")
    if isinstance(color, dict):
        color = color.get("color")
    assert color == "red" or row.get("requires_human")
    _assert_no_legacy_leak(_blob(row.get("suggested_response"), json.dumps(row.get("hits") or [])))


def test_all_transmission_seed_emails_no_leak(tx_root: Path):
    svc = EmailService(root=tx_root, vertical="transmission")
    out = svc.seed_demo(clear=True, process=True, vertical="transmission")
    assert out["seeded"] == len(TRANSMISSION_DEMO_EMAILS)
    assert out.get("inventory_source") == "transmission_dms"
    rows = svc.list(limit=50)
    assert len(rows) == len(TRANSMISSION_DEMO_EMAILS)
    combined = []
    for r in rows:
        combined.append(r.get("suggested_response") or "")
        combined.append(json.dumps(r.get("hits") or []))
        tl = r.get("traffic_light")
        if isinstance(tl, dict):
            combined.append(str(tl.get("reason") or ""))
            combined.append(str(tl.get("color") or ""))
        else:
            combined.append(str(r.get("traffic_reason") or ""))
    blob = "\n".join(combined)
    _assert_no_legacy_leak(blob, context="all seeds")
    # Explicit screenshot case
    drum = next(r for r in rows if "10R80 reaction drum" in (r.get("subject") or ""))
    dblob = _blob(drum.get("suggested_response"), json.dumps(drum.get("hits") or []))
    assert "brake" not in dblob.lower()
    assert "civic" not in dblob.lower()


def test_generic_vertical_still_uses_rag_path(tmp_path: Path, monkeypatch):
    """Generic mode may still construct PartsRAGEngine — transmission must not."""
    monkeypatch.delenv("PARRTS_VERTICAL", raising=False)
    monkeypatch.delenv("EMAIL_VERTICAL", raising=False)
    root = tmp_path / "generic"
    root.mkdir()
    svc = EmailService(root=root, vertical="generic")
    assert svc.vertical == "generic"
    eng = svc._get_engine()
    # May be None if RAG deps missing; if present must NOT be transmission adapter
    if eng is not None:
        assert not getattr(eng, "is_transmission_adapter", False)


def test_transmission_mode_no_engine_means_review_not_rag(tx_root: Path):
    """If adapter init fails closed, still no PartsRAGEngine."""
    svc = EmailService(root=tx_root, vertical="transmission", engine=TransmissionPartsAdapter(tx_root))
    spec = PartsQuoteSpecialist(engine=svc._get_engine())
    res = spec.handle(
        subject="Need 10R80 reaction drum ASAP",
        body="10R80 reaction drum qty 1",
        classification={"extracted_info": {"parts_requested": ["10R80 reaction drum"]}},
    )
    assert res.ok
    _assert_no_legacy_leak(_blob(res.suggested_response, json.dumps(res.hits)))
    assert (res.data or {}).get("inventory_source") == "transmission_dms"
