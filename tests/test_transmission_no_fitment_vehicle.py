"""No-fitment vehicle/family safety: named vehicle + family without canonical support."""
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
    dms._tmp = tmp  # type: ignore[attr-defined]
    return dms


def test_prius_6l80_no_fitment_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("CVT pump for Prius 6L80", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason
    low = a.ambiguity_reason.lower()
    assert "fitment" in low or "verif" in low


def test_tahoe_6l80_supported_still_resolves():
    dms = _dms()
    a = answer_transmission_inquiry(
        "Do you have a pump for a 2011 Tahoe 6L80?", dms
    )
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_e09_tahoe_multi_family_still_resolves():
    dms = _dms()
    a = answer_transmission_inquiry("4L60E pump for a 2011 Tahoe 6L80", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_f150_6l80_conflict_still_escalates():
    dms = _dms()
    a = answer_transmission_inquiry("6L80 pump for an F-150", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None


def test_family_only_without_vehicle_still_resolves():
    dms = _dms()
    a = answer_transmission_inquiry("Do you have a 6L80 pump?", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_competing_signal_still_escalates():
    dms = _dms()
    a = answer_transmission_inquiry(
        "pump or valve body for 6L80 — not sure which", dms
    )
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
