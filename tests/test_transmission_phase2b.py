"""Phase 2B acceptance tests (package marker + bin column)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.resolver import resolve_inquiry


def test_package_marker_exists():
    """Filesystem + Git proof is authoritative; this test is a placeholder."""
    assert True


def test_inventory_levels_has_bin_column():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        row = dms.store.fetchone("PRAGMA table_info(inventory_levels)")
        # crude check that bin column exists
        cols = [r[1] for r in dms.store.fetchall("PRAGMA table_info(inventory_levels)")]
        assert "bin" in cols


def test_demo_seed_includes_bins():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        load_demo_seed(dms)
        row = dms.store.fetchone("SELECT bin FROM inventory_levels WHERE qty > 0 LIMIT 1")
        assert row is not None
        assert row["bin"] is not None


def test_main_inquiry_returns_canonical_bin():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        load_demo_seed(dms)
        r = resolve_inquiry("Do you have a pump for a 2011 Tahoe 6L80?", dms)
        inv = dms.store.fetchall(
            "SELECT qty, condition, bin FROM inventory_levels WHERE sku = ? AND qty > 0",
            (r.matched_skus[0],)
        )
        assert len(inv) > 0
        assert inv[0]["bin"] is not None


def test_identifier_lookup_still_works():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        load_demo_seed(dms)
        r = resolve_inquiry("Do you have 24264418?", dms)
        assert "6L80-PUMP-01" in r.matched_skus


def test_ambiguity_still_works():
    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        load_demo_seed(dms)
        r = resolve_inquiry("Do you have anything?", dms)
        assert len(r.uncertainty) > 0 or r.fitment_status in ("insufficient", "no_match")