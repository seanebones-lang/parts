"""Tests for parent SKU expansion."""

from __future__ import annotations

from parrts.models import PartRecord, RankedHit
from parrts.parent_expand import base_sku, expand_parent_hits


def _part(sku: str, loc: str, stock: int = 5) -> PartRecord:
    return PartRecord(
        sku=sku,
        name="Brake Pads",
        location=loc,
        stock=stock,
        price=40.0,
        make="Honda",
        model="Civic",
        year="2019",
        category="brakes",
    )


def test_base_sku_strips_location_suffix():
    assert base_sku("BP-HC19-L4") == "BP-HC19"
    assert base_sku("BP-HC19") == "BP-HC19"
    assert base_sku("OF-TC-L12") == "OF-TC"


def test_expand_parent_adds_siblings():
    p1 = _part("BP-HC19-L1", "Chicago North", 6)
    p2 = _part("BP-HC19-L2", "O'Hare Auto", 3)
    p3 = _part("BP-HC19-L4", "Wrigley Dealership", 14)
    other = _part("OF-TC-L1", "Chicago North", 9)
    all_parts = [p1, p2, p3, other]
    hits = [RankedHit(part=p1, score=0.9, dense_score=0.8, sparse_score=1.0, rrf_score=0.03)]
    expanded = expand_parent_hits(hits, all_parts, max_siblings=7, top_parents=1)
    skus = {h.part.sku for h in expanded}
    assert "BP-HC19-L1" in skus
    assert "BP-HC19-L2" in skus
    assert "BP-HC19-L4" in skus
    assert "OF-TC-L1" not in skus
    # primary stays first
    assert expanded[0].part.sku == "BP-HC19-L1"
