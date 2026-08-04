"""Catalog admin, order lifecycle, invoice PDF, RBAC unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from parrts.dms.service import DmsService
from parrts.rbac import can, describe, require


@pytest.fixture
def dms(tmp_path: Path) -> DmsService:
    svc = DmsService(root=tmp_path, backend="sqlite")
    svc.ensure_schema()
    return svc


def test_upsert_and_csv_import(dms: DmsService) -> None:
    out = dms.upsert_catalog_part(
        sku="ADM-1",
        name="Admin Pad",
        make="Honda",
        list_price=12.5,
        location_qty={"L1": 4},
    )
    assert out["ok"] is True
    assert out["part"]["sku"] == "ADM-1"
    cats = dms.list_catalog(q="ADM")
    assert any(c["sku"] == "ADM-1" for c in cats)

    csv_text = "sku,name,make,list_price,L1\nCSV-9,Csv Part,Toyota,9.99,3\n"
    imp = dms.import_catalog_csv(csv_text)
    assert imp["upserted"] == 1
    assert imp["ok"] is True
    assert any(c["sku"] == "CSV-9" for c in dms.list_catalog())


def test_order_lifecycle_and_invoice(dms: DmsService, tmp_path: Path) -> None:
    dms.seed_demo(n_skus=5, locations=2)
    cust = dms.create_customer(name="Life Cycle", email="lc@test.local")
    inv = next(r for r in dms.list_inventory() if int(r["qty"]) >= 2)
    qty_before = int(inv["qty"])
    order = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    oid = int(order["id"])
    assert dms.get_order(oid)["status"] == "open"
    assert dms.get_order(oid)["total"] > 0

    dms.set_order_status(oid, "picking")
    assert dms.get_order(oid)["status"] == "picking"

    inv_path = tmp_path / "inv.pdf"
    pdf = dms.write_invoice_pdf(oid, path=inv_path)
    assert pdf["ok"] is True
    assert Path(pdf["path"]).is_file()
    assert Path(pdf["path"]).read_bytes()[:4] == b"%PDF"
    assert dms.get_order(oid)["status"] == "invoiced"

    dms.set_order_status(oid, "completed")
    assert dms.get_order(oid)["status"] == "completed"

    # cancel path restores stock
    order2 = dms.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": inv["sku"], "location_id": inv["location_id"], "qty": 1}],
    )
    mid = next(
        r
        for r in dms.list_inventory()
        if r["sku"] == inv["sku"] and int(r["location_id"]) == int(inv["location_id"])
    )
    after_create = int(mid["qty"])
    dms.set_order_status(int(order2["id"]), "cancelled")
    restored = next(
        r
        for r in dms.list_inventory()
        if r["sku"] == inv["sku"] and int(r["location_id"]) == int(inv["location_id"])
    )
    assert int(restored["qty"]) == after_create + 1
    assert qty_before >= after_create


def test_rbac_matrix() -> None:
    assert can("counter", "orders.read")
    assert not can("counter", "catalog.import")
    assert can("manager", "catalog.import")
    assert can("admin", "dms.seed")
    with pytest.raises(PermissionError):
        require("counter", "admin")
    d = describe("manager")
    assert d["role"] == "manager"
    assert "catalog.write" in d["permissions"]
