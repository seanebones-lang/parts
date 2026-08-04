"""Live Postgres DMS dual-mode tests — skip when DB unreachable."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from parrts.dms.backend import build_postgres_url_from_env

pytestmark = pytest.mark.postgres_dms


def _pg_url() -> str | None:
    return (
        os.environ.get("DMS_DATABASE_URL")
        or os.environ.get("PARRTS_TEST_PG_URL")
        or build_postgres_url_from_env()
    )


def _can_connect(url: str) -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(url, connect_timeout=2)
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="module")
def pg_url() -> str:
    url = _pg_url()
    if not url:
        pytest.skip("No DMS_DATABASE_URL / POSTGRES_HOST for postgres DMS tests")
    # normalize
    if url.startswith("postgresql+psycopg2://"):
        url = "postgresql://" + url[len("postgresql+psycopg2://") :]
    if not _can_connect(url):
        pytest.skip(f"Postgres unreachable for DMS tests: {url.split('@')[-1]}")
    return url


def test_alembic_upgrade_and_seed(pg_url: str, tmp_path: Path) -> None:
    from parrts.dms.migrate import upgrade_head
    from parrts.dms.service import DmsService

    mig = upgrade_head(database_url=pg_url)
    assert mig["ok"] is True, mig

    # Isolate data with unique SKU prefix via small seed + cleanup of our customers
    svc = DmsService(root=tmp_path, backend="postgres", database_url=pg_url)
    st0 = svc.status()
    assert st0["backend"] == "postgres"
    assert st0["ok"] is True

    seed = svc.seed_demo(seed=99, n_skus=3, locations=2)
    assert seed["ok"] is True
    assert seed["parts_upserted"] == 3

    cust = svc.create_customer(name=f"PG Test {uuid.uuid4().hex[:8]}", email="pg@test.local")
    inv = svc.list_inventory()
    assert len(inv) >= 3
    # pick a line with stock
    line = next(r for r in inv if int(r["qty"]) > 0)
    order = svc.create_order(
        customer_id=int(cust["id"]),
        lines=[{"sku": line["sku"], "location_id": line["location_id"], "qty": 1}],
        notes="postgres dual-mode test",
    )
    assert order["id"] > 0
    assert len(order["lines"]) == 1

    st = svc.status()
    assert st["catalog_parts"] >= 3
    assert st["orders"] >= 1
