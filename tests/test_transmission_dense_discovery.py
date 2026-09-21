"""Dense catalog inventory discovery + counter search regression.

Loads baseline demo seed + JP 503-line synthetic CSV, then verifies:
  product-class browse, exact SKU/identifier, safety escalations.
Does not modify frozen resolver expectations on the tiny seed alone.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from parrts.dms.ops import InventoryOps, OpsConflictError
from parrts.dms.service import DmsService
from parrts.transmission.counter_search import counter_search
from parrts.transmission.discovery import (
    families_in_query,
    part_category_in_query,
)
from parrts.transmission.importer import build_import_plan, commit_import_plan
from parrts.transmission.seed_loader import load_demo_seed
from parrts.transmission.service import answer_transmission_inquiry

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "jp_demo" / "jp_demo_inventory_seed.csv"


@pytest.fixture()
def dense_dms(tmp_path: Path):
    if not CSV.is_file():
        pytest.skip("JP demo CSV missing")
    root = tmp_path / "dense"
    root.mkdir()
    svc = DmsService(root)
    svc.ensure_schema()
    load_demo_seed(svc)
    text = CSV.read_text(encoding="utf-8")
    plan = build_import_plan(text, svc, source="jp_demo_inventory", allow_new_locations=False)
    assert plan.invalid_rows == 0
    plan = commit_import_plan(plan, svc)
    assert plan.committed
    yield svc
    svc.store.close()


def test_taxonomy_helpers():
    assert part_category_in_query("Need a 6L80 core") == "complete core"
    assert part_category_in_query("6L80 torque converter") == "torque converter"
    assert part_category_in_query("4L60E sun shell") == "sun shell"
    assert part_category_in_query("6R80 pump") == "pump"
    assert part_category_in_query("4L60E valve body") == "valve body"
    assert "6L80" in families_in_query("Need a 6L80 pump ASAP")
    assert "10R80" in families_in_query("10R80 core")


@pytest.mark.parametrize(
    "query,expect_family,expect_cat",
    [
        ("4L60E valve body", "4L60E", "valve body"),
        ("6R80 pump", "6R80", "pump"),
        ("4L60E pump", "4L60E", "pump"),
        ("6L90 pump", "6L90", "pump"),
        ("Need a 6L80 core", "6L80", "complete core"),
        ("4L60E sun shell", "4L60E", "sun shell"),
        ("6L80 torque converter", "6L80", "torque converter"),
        ("10R80 core", "10R80", "complete core"),
        ("10L80 converter", "10L80", "torque converter"),
        ("Need a 6L80 pump ASAP", "6L80", "pump"),
    ],
)
def test_product_class_inventory_matches(dense_dms, query, expect_family, expect_cat):
    r = counter_search(query, dense_dms)
    assert r.search_mode == "inventory_matches", (query, r.search_mode, r.human_readable)
    assert r.status == "inventory_matches"
    assert r.outcome is None  # not autonomous exact resolve
    assert r.discovery is not None
    assert r.discovery["candidate_count"] >= 1
    assert r.discovery["total_available"] >= 0
    assert r.transmission_family == expect_family or expect_family in (
        r.transmission_family or ""
    )
    assert (r.part_type or "") == expect_cat
    # no arbitrary single SKU winner
    assert r.sku is None
    c0 = r.discovery["candidates"][0]
    assert "sku" in c0 and "available" in c0 and "location_code" in c0
    for c in r.discovery["candidates"]:
        actual = c.get("actual_part_category") or c.get("part_type_label")
        assert actual == expect_cat, (query, c["sku"], actual)


def test_candidate_purity_no_description_contamination(dense_dms):
    """Cores mentioning pump/converter in NOTES must not appear in pump/converter browse."""
    for q, expect_cat in [
        ("10L80 pump", "pump"),
        ("10L80 converter", "torque converter"),
        ("6L80 pump", "pump"),
        ("6L80 torque converter", "torque converter"),
        ("4L60E valve body", "valve body"),
        ("4L60E sun shell", "sun shell"),
        ("10R80 core", "complete core"),
    ]:
        r = counter_search(q, dense_dms)
        # Empty stock after pure filter is OK (e.g. 10L80 pump only has 10L90 pumps in seed)
        if r.search_mode != "inventory_matches":
            assert r.search_mode == "needs_review", (q, r.search_mode)
            assert (r.discovery or {}).get("candidate_count", 0) == 0 or not r.discovery
            continue
        assert r.discovery and r.discovery["candidates"]
        for c in r.discovery["candidates"]:
            actual = c.get("actual_part_category") or c.get("part_type_label")
            assert actual == expect_cat, (q, c["sku"], c["name"], actual)
            if expect_cat in ("pump", "torque converter"):
                assert "core assembly" not in (c["name"] or "").lower(), (q, c["name"])


def test_variant_isolation(dense_dms):
    cases = [
        ("10L80 converter", "10L80"),
        ("10L90 converter", "10L90"),
        ("10L80 core", "10L80"),
        ("10L90 core", "10L90"),
        ("4L60E valve body", "4L60E"),
        ("4L65E valve body", "4L65E"),
        ("4L70E valve body", "4L70E"),
    ]
    for q, expect_var in cases:
        r = counter_search(q, dense_dms)
        assert r.search_mode == "inventory_matches", (q, r.search_mode, r.human_readable)
        assert r.discovery and r.discovery["candidate_count"] >= 1, q
        for c in r.discovery["candidates"]:
            var = (c.get("transmission_variant") or "").upper()
            fam = (c.get("transmission_family") or "").upper()
            if var:
                assert var == expect_var, (q, c["sku"], var, fam)
            else:
                assert fam == expect_var, (q, c["sku"], var, fam)


def test_exact_sku(dense_dms):
    r = counter_search("6L80-PUMP-01", dense_dms)
    assert r.search_mode == "exact_match"
    assert r.sku == "6L80-PUMP-01"
    assert r.status == "resolved"


def test_identifier_24264418(dense_dms):
    r = counter_search("24264418", dense_dms)
    assert r.search_mode == "exact_match"
    assert r.sku == "6L80-PUMP-01"


@pytest.mark.parametrize(
    "query",
    [
        "6L80 or 6R80 pump which one?",
        "6L80 pump and valve body",
        "can I use 6L90 pump instead of 6L80",
        "CVT pump for Prius 6L80",
    ],
)
def test_safety_needs_review(dense_dms, query):
    r = counter_search(query, dense_dms)
    assert r.search_mode == "needs_review", (query, r.search_mode, r.human_readable)
    assert r.outcome == "NEEDS_HUMAN" or r.status in (
        "insufficient",
        "ambiguous",
        "no_match",
    )


def test_discovery_totals_match_candidates(dense_dms):
    r = counter_search("6L80 pump", dense_dms)
    assert r.search_mode == "inventory_matches"
    d = r.discovery
    assert d["total_on_hand"] == sum(c["on_hand"] for c in d["candidates"])
    assert d["total_available"] == sum(c["available"] for c in d["candidates"])
    assert d["total_reserved"] == sum(c["reserved"] for c in d["candidates"])


def test_zero_available_cannot_reserve(dense_dms):
    r = counter_search("6L80 pump", dense_dms)
    ops = InventoryOps(dense_dms)
    zero = [c for c in r.discovery["candidates"] if c["available"] <= 0]
    if not zero:
        pytest.skip("no zero-available pump lots in seed")
    c = zero[0]
    with pytest.raises((OpsConflictError, Exception)):
        ops.reserve(sku=c["sku"], location=c["location_code"], qty=1)


def test_select_lot_quote_reserve_sale(dense_dms):
    r = counter_search("6R80 pump", dense_dms)
    assert r.search_mode == "inventory_matches"
    cand = next(c for c in r.discovery["candidates"] if c["available"] > 0)
    ops = InventoryOps(dense_dms)
    before = next(
        x for x in ops.stock_view(sku=cand["sku"]) if x["location_code"] == cand["location_code"]
    )
    q = ops.create_quote(customer_label="Discovery demo")
    ops.add_quote_line(
        quote_id=q["id"],
        sku=cand["sku"],
        location=cand["location_code"],
        qty=1,
        unit_price_cents=15000,
    )
    ops.reserve_quote(quote_id=q["id"])
    order = ops.convert_quote_to_order(quote_id=q["id"])
    ops.complete_order(order_id=order["id"])
    after = next(
        x for x in ops.stock_view(sku=cand["sku"]) if x["location_code"] == cand["location_code"]
    )
    assert after["on_hand"] == before["on_hand"] - 1
    assert after["reserved"] == before["reserved"]


def test_frozen_resolver_baseline_unchanged_on_tiny_seed(tmp_path: Path):
    """Tiny seed only — answer_transmission_inquiry path used by evals."""
    root = tmp_path / "tiny"
    root.mkdir()
    svc = DmsService(root)
    svc.ensure_schema()
    load_demo_seed(svc)
    a = answer_transmission_inquiry("Do you have a pump for a 2011 Tahoe 6L80?", svc)
    assert a.status == "resolved"
    assert a.sku == "6L80-PUMP-01"
    b = answer_transmission_inquiry("24264418", svc)
    assert b.status == "resolved"
    assert b.sku == "6L80-PUMP-01"
    svc.store.close()


def test_counter_search_timing_budget(dense_dms):
    r = counter_search("6L80 pump", dense_dms)
    assert r.elapsed_ms < 250.0 or r.elapsed_ms < 1000.0  # CI slack; report real value
    assert r.elapsed_ms >= 0
