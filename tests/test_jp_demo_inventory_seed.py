"""JP demo inventory seed builder — deterministic CSV from workbook."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.build_jp_demo_inventory import (
    CSV_HEADERS,
    DEFAULT_CSV,
    DEFAULT_XLSX,
    build_rows,
    validate_rows,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not DEFAULT_XLSX.is_file(), reason="workbook not present")
def test_build_jp_demo_inventory_valid_and_stable(tmp_path: Path):
    rows, report = build_rows(DEFAULT_XLSX)
    assert report.workbook_inventory_rows == 500
    assert report.emitted_rows >= 500  # 500 workbook + canonical top-ups
    assert report.unique_skus == report.emitted_rows
    assert report.skipped == []
    errs = validate_rows(rows)
    assert errs == []

    # quantities and identity
    skus = [r["sku"] for r in rows]
    assert len(skus) == len(set(skus))
    for r in rows:
        qty = int(r["qty"])
        assert qty >= 0
        assert r["location"] in ("CHI-N", "OHARE")
        assert r["condition"] in ("new", "used", "rebuilt", "core")
        assert r["transmission_family"]
        assert r["name"]
        assert r["verification_status"] == "unverified"

    # priority families present
    fams = {r["transmission_family"] for r in rows}
    for f in ("4L60E", "6L80", "6R80", "4L80E", "6L90", "10R80", "10L80"):
        assert f in fams

    # flagship part types present in names/descriptions
    blob = " ".join(r["name"] + " " + r["description"] for r in rows).lower()
    assert "valve body" in blob
    assert "pump" in blob
    assert "core" in blob
    assert "torque converter" in blob or "converter" in blob

    # canonical top-ups present
    top = {r["sku"] for r in rows}
    assert "4L60E-VB-01" in top
    assert "6R80-PUMP-01" in top
    assert "6L80-PUMP-01" in top

    # byte-stable write
    out1 = tmp_path / "a.csv"
    out2 = tmp_path / "b.csv"
    write_csv(rows, out1)
    write_csv(rows, out2)
    assert out1.read_bytes() == out2.read_bytes()

    # header contract
    with out1.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CSV_HEADERS


@pytest.mark.skipif(not DEFAULT_CSV.is_file(), reason="generated csv not present")
def test_checked_in_csv_matches_rebuild():
    rows, _ = build_rows(DEFAULT_XLSX)
    from io import StringIO

    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_HEADERS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({h: r.get(h, "") for h in CSV_HEADERS})
    assert buf.getvalue().encode("utf-8") == DEFAULT_CSV.read_bytes()


def test_import_preview_accepts_generated_csv(tmp_path: Path):
    if not DEFAULT_XLSX.is_file():
        pytest.skip("workbook missing")
    from parrts.dms.service import DmsService
    from parrts.transmission.importer import build_import_plan
    from parrts.transmission.seed_loader import load_demo_seed

    rows, _ = build_rows(DEFAULT_XLSX)
    csv_path = tmp_path / "seed.csv"
    write_csv(rows, csv_path)

    root = tmp_path / "dms"
    root.mkdir()
    svc = DmsService(root)
    svc.ensure_schema()
    load_demo_seed(svc)
    # keep store open for plan build
    text = csv_path.read_text(encoding="utf-8")
    plan = build_import_plan(
        text,
        svc,
        source="jp_demo_test",
        allow_new_locations=False,
    )
    assert plan.invalid_rows == 0, [
        (r.sku, r.errors) for r in plan.rows if r.errors
    ][:8]
    assert plan.total_rows == len(rows)
    assert plan.file_errors == []
    svc.store.close()
