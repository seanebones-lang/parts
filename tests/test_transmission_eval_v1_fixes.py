"""Bounded fixes from eval v1: conflict safety + counter-language tokens."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry


def _dms():
    tmp = TemporaryDirectory()
    dms = DmsService(Path(tmp.name))
    dms.ensure_schema()
    load_demo_seed(dms)
    # keep tmp alive via attribute
    dms._tmp = tmp  # type: ignore[attr-defined]
    return dms


def test_f150_6l80_conflict_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("6L80 pump for an F-150", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason and "conflict" in a.ambiguity_reason.lower()


def test_tahoe_conflicting_families_prefers_vehicle_consistent():
    dms = _dms()
    a = answer_transmission_inquiry(
        "4L60E pump for a 2011 Tahoe 6L80", dms
    )
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_vb_abbreviation():
    dms = _dms()
    a = answer_transmission_inquiry("6L80 VB in stock?", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-VB-01"


def test_valv_misspelling():
    dms = _dms()
    a = answer_transmission_inquiry("need a 6l80 valv body rebuilt", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-VB-01"


def test_pmp_misspelling():
    dms = _dms()
    a = answer_transmission_inquiry("need 6l80 pmp asap", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_drum_part_type():
    dms = _dms()
    a = answer_transmission_inquiry("do you have a drum for 10R80?", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "10R80-DRUM-01"
