"""Unit tests for traffic-light policy."""

from __future__ import annotations

from parrts.models import PartRecord, RankedHit
from parrts.policy import evaluate_traffic_light, policy_for_hits


def _part(stock: int = 5) -> PartRecord:
    return PartRecord(
        sku="BP-HC19-L1",
        name="Brake Pads 2019 Honda Civic",
        location="Chicago North",
        stock=stock,
        price=45.0,
        make="Honda",
        model="Civic",
        year="2019",
        category="brakes",
    )


def test_green_high_sim_healthy_stock():
    tl = evaluate_traffic_light(0.80, 5)
    assert tl.color == "green"
    assert tl.confidence >= 0.55
    assert tl.stock == 5
    assert any("Reserve" in a or "reserve" in a.lower() for a in tl.actions)


def test_yellow_low_stock():
    tl = evaluate_traffic_light(0.80, 2)
    assert tl.color == "yellow"
    assert tl.stock == 2


def test_yellow_mid_sim():
    tl = evaluate_traffic_light(0.40, 10)
    assert tl.color == "yellow"


def test_red_zero_stock():
    tl = evaluate_traffic_light(0.90, 0)
    assert tl.color == "red"
    assert tl.stock == 0
    assert any("backorder" in a.lower() or "other location" in a.lower() for a in tl.actions)


def test_red_low_sim():
    tl = evaluate_traffic_light(0.10, 20)
    assert tl.color == "red"
    assert tl.similarity == 0.1


def test_boundary_sim_green():
    tl = evaluate_traffic_light(0.55, 3)
    assert tl.color == "green"


def test_boundary_stock_one_yellow():
    tl = evaluate_traffic_light(0.90, 1)
    assert tl.color == "yellow"


def test_policy_for_empty_hits():
    tl = policy_for_hits([])
    assert tl.color == "red"
    assert tl.confidence <= 0.2


def test_policy_for_hits_uses_top():
    hits = [
        RankedHit(part=_part(stock=5), score=0.9),
        RankedHit(part=_part(stock=0), score=0.5),
    ]
    tl = policy_for_hits(hits)
    assert tl.color == "green"
    assert tl.stock == 5
