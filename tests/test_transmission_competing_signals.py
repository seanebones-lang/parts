"""Competing-signal safety: multi-part / comparative / multi-item → NEEDS_HUMAN."""
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


def test_pump_or_valve_body_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry(
        "pump or valve body for 6L80 — not sure which", dms
    )
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason
    assert "part-type" in a.ambiguity_reason.lower() or "competing" in a.ambiguity_reason.lower()


def test_family_comparison_same_as_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("is 6R80 pump same as 6L80 pump?", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason
    assert "same-as" in a.ambiguity_reason.lower() or "compar" in a.ambiguity_reason.lower()


def test_instead_of_substitution_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("can I use 6L90 pump instead of 6L80?", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason
    low = a.ambiguity_reason.lower()
    assert "substitution" in low or "instead" in low


def test_which_one_multi_family_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("6L80 6L90 6R80 pump which one", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason
    assert "which-one" in a.ambiguity_reason.lower() or "which one" in a.ambiguity_reason.lower()


def test_and_both_two_parts_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("6L80 pump AND 6L80 valve body both now", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None
    assert a.ambiguity_reason


def test_clean_single_family_part_still_resolves():
    dms = _dms()
    a = answer_transmission_inquiry("Do you have a 6L80 pump?", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_e09_vehicle_consistent_family_no_regress():
    """Eval v1 E09: multi family tokens + vehicle evidence still selects 6L80."""
    dms = _dms()
    a = answer_transmission_inquiry("4L60E pump for a 2011 Tahoe 6L80", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_safe_interchange_identify_still_resolves():
    """Asymmetric interchange identify (not a symmetric same-as comparison)."""
    dms = _dms()
    a = answer_transmission_inquiry("Does 6L80 pump interchange with 6L90?", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_same_as_but_for_anchor_still_resolves():
    dms = _dms()
    a = answer_transmission_inquiry("same as 6L90 pump but for 6L80?", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"


def test_contradictory_pump_and_vb_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry(
        "6L80 pump that is also a 6R80 valve body right now", dms
    )
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None


def test_crossover_multi_family_needs_human():
    dms = _dms()
    a = answer_transmission_inquiry("cross over from 6L90 heavy pump to 6L80", dms)
    assert a.outcome == "NEEDS_HUMAN"
    assert a.sku is None


def test_plural_pumps_still_resolves():
    """Word-boundary part-type must still match plural 'pumps'."""
    dms = _dms()
    a = answer_transmission_inquiry("how many 6L80 pumps on hand", dms)
    assert a.outcome == "RESOLVED"
    assert a.sku == "6L80-PUMP-01"
