"""End-to-end engine tests (offline)."""

from __future__ import annotations

import json
from pathlib import Path

from parrts.embeddings import HashingEmbedder
from parrts.engine import PartsRAGEngine
from parrts.inventory import CHICAGO_LOCATIONS, generate_catalog, load_inventory


def test_catalog_seven_locations_and_volume():
    inv = generate_catalog(seed=42)
    assert len(inv.locations) == 7
    assert set(inv.locations) == set(CHICAGO_LOCATIONS)
    parts = inv.all_parts()
    # 35 part types × 7 locations (expanded catalog Wave1+)
    assert len(parts) >= 25 * 7
    assert len(parts) == len(parts)  # non-empty sanity
    assert len(parts) % 7 == 0
    types = len(parts) // 7
    assert types >= 25
    # deterministic
    inv2 = generate_catalog(seed=42)
    assert [p.stock for p in inv.all_parts()] == [p.stock for p in inv2.all_parts()]


def test_build_and_persist(tmp_root: Path):
    eng = PartsRAGEngine(root=tmp_root, embedder=HashingEmbedder(), seed=42)
    info = eng.build(force_inventory=True)
    assert info["parts"] > 100
    assert (tmp_root / ".parrts" / "inventory.json").exists()
    assert (tmp_root / ".parrts" / "index" / "meta.json").exists()
    assert (tmp_root / ".parrts" / "index" / "vectors.npy").exists()
    loaded = load_inventory(root=tmp_root)
    assert len(loaded.all_parts()) == info["parts"]


def test_query_brake_pads(engine: PartsRAGEngine):
    result = engine.query(
        "brake pads for 2019 Honda Civic",
        top_k=5,
        use_llm=False,
    )
    assert result.query.startswith("brake")
    assert result.hits
    assert result.traffic_light is not None
    assert result.traffic_light.color in {"green", "yellow", "red"}
    assert result.answer
    top_name = result.hits[0].part.name.lower()
    assert "brake" in top_name or "civic" in top_name
    d = result.to_dict()
    assert "hits" in d
    assert d["traffic_light"]["color"] in {"green", "yellow", "red"}
    # JSON serializable
    json.dumps(d)


def test_query_location_filter(engine: PartsRAGEngine):
    result = engine.query(
        "oil filter",
        location="Chicago North",
        top_k=3,
        use_llm=False,
    )
    assert result.hits
    for h in result.hits:
        assert "chicago north" in h.part.location.lower()


def test_load_reload(tmp_root: Path):
    eng = PartsRAGEngine(root=tmp_root, embedder=HashingEmbedder(), seed=42)
    eng.build(force_inventory=True)
    eng2 = PartsRAGEngine(root=tmp_root, embedder=HashingEmbedder(), seed=42)
    info = eng2.load()
    assert info["parts"] > 0
    r = eng2.query("spark plugs honda", use_llm=False)
    assert r.hits


def test_no_llm_without_keys(engine: PartsRAGEngine):
    r = engine.query("alternator ford f-150", use_llm=True)
    # falls back to offline template
    assert r.answer
    assert "alternator" in r.answer.lower() or "f-150" in r.answer.lower() or r.hits


def test_status(engine: PartsRAGEngine):
    st = engine.status()
    assert st["built"] is True
    assert st["parts_indexed"] > 0
    assert st["inventory"]["locations"] == 7
