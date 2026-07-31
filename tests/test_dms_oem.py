"""Offline DMS + OEM feed tests (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from parrts.dms.oem import FileOemFeed, SyntheticOemFeed
from parrts.dms.service import DmsService, InsufficientStockError

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_OEM = REPO_ROOT / "data" / "oem" / "sample_oem_catalog.json"


@pytest.fixture
def dms(tmp_path: Path) -> DmsService:
    svc = DmsService(root=tmp_path)
    svc.ensure_schema()
    return svc


def test_seed_synthetic(dms: DmsService) -> None:
    stats = dms.seed_demo(seed=42, n_skus=40, locations=7)
    assert stats["ok"] is True
    assert stats["parts_upserted"] == 40
    assert stats["status"] == "ok"

    status = dms.status()
    assert status["catalog_parts"] == 40
    assert status["locations"] == 7
    assert status["inventory_rows"] == 40 * 7
    assert status["inventory_units"] > 0
    assert status["last_oem_sync"] is not None
    assert status["last_oem_sync"]["status"] == "ok"

    inv = dms.list_inventory()
    assert len(inv) == 280
    # Deterministic: same seed → same first SKU
    feed_skus = [p["sku"] for p in SyntheticOemFeed(seed=42, n_skus=40).iter_parts()]
    db_skus = sorted({r["sku"] for r in inv})
    assert sorted(feed_skus) == db_skus


def test_sync_file_sample(dms: DmsService) -> None:
    assert SAMPLE_OEM.exists(), f"missing sample feed: {SAMPLE_OEM}"
    feed = FileOemFeed(SAMPLE_OEM)
    stats = dms.sync_oem(feed, source="file")
    assert stats["ok"] is True
    assert stats["parts_upserted"] == 15

    status = dms.status()
    assert status["catalog_parts"] == 15
    # Multi-location rows
    assert status["inventory_rows"] == 15 * 7

    one = dms.list_inventory(location="CHI-N")
    assert len(one) == 15
    skus = {r["sku"] for r in one}
    assert "OEM-SAMPLE-BP-HC19" in skus

    # qty matches sample for known row
    bp = next(r for r in one if r["sku"] == "OEM-SAMPLE-BP-HC19")
    assert bp["qty"] == 12


def test_create_customer_order_reduces_stock(dms: DmsService) -> None:
    dms.seed_demo(seed=42, n_skus=10, locations=7)
    inv_before = dms.list_inventory(location="CHI-N")
    assert inv_before
    target = next(r for r in inv_before if r["qty"] >= 3)
    sku = target["sku"]
    loc_id = int(target["location_id"])
    qty_before = int(target["qty"])

    customer = dms.create_customer(
        name="Test Buyer",
        email="buyer@example.com",
        phone="555-0100",
        company="Demo Garage",
    )
    assert customer["id"] >= 1
    assert len(dms.list_customers()) == 1

    order = dms.create_order(
        customer_id=customer["id"],
        lines=[{"sku": sku, "location_id": loc_id, "qty": 2}],
        notes="test reserve",
    )
    assert order["id"] >= 1
    assert len(order["lines"]) == 1
    assert order["lines"][0]["qty"] == 2

    # Inventory decreased
    after = dms.list_inventory(location="CHI-N")
    row = next(r for r in after if r["sku"] == sku)
    assert int(row["qty"]) == qty_before - 2

    orders = dms.list_orders()
    assert len(orders) == 1
    assert orders[0]["id"] == order["id"]
    assert orders[0]["lines"][0]["sku"] == sku


def test_order_insufficient_stock(dms: DmsService) -> None:
    feed = FileOemFeed(SAMPLE_OEM)
    dms.sync_oem(feed, source="file")
    # LOGAN has 0 rotors in sample
    inv = dms.list_inventory(location="LOGAN")
    zero = next(r for r in inv if r["sku"] == "OEM-SAMPLE-BR-HC")
    assert zero["qty"] == 0
    cust = dms.create_customer(name="No Stock Co")
    with pytest.raises(InsufficientStockError):
        dms.create_order(
            customer_id=cust["id"],
            lines=[{"sku": "OEM-SAMPLE-BR-HC", "location_id": zero["location_id"], "qty": 1}],
        )


def test_export_parrts_inventory_format(dms: DmsService, tmp_path: Path) -> None:
    dms.seed_demo(seed=42, n_skus=5, locations=3)
    path = dms.export_parrts_inventory()
    assert path.exists()
    assert path.name == "inventory_from_dms.json"

    from parrts.inventory import load_inventory

    inv = load_inventory(path=path)
    parts = inv.all_parts()
    assert len(parts) == 5 * 3
    assert all(p.sku and p.location for p in parts)


def test_reindex_rag_makes_oem_queryable(dms: DmsService) -> None:
    """DMS seed + reindex → hybrid query returns DMS/OEM SKUs."""
    dms.seed_demo(seed=42, n_skus=20, locations=7)
    result = dms.reindex_rag()
    assert result.get("ok") is True, result
    assert (dms.root / ".parrts" / "inventory.json").exists()

    from parrts.embeddings import HashingEmbedder
    from parrts.engine import PartsRAGEngine

    eng = PartsRAGEngine(root=dms.root, embedder=HashingEmbedder())
    eng.ensure_ready()
    qr = eng.query("brake pads Honda", use_llm=False, top_k=5)
    hits = qr.to_dict().get("hits") or []
    assert hits, qr.to_dict()
    # After DMS reindex, catalog is OEM-synthetic (prefixes OEM-)
    top_skus = " ".join(str(h.get("sku", "")) for h in hits)
    assert "OEM" in top_skus or hits[0].get("name"), hits
