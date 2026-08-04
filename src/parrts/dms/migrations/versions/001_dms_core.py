"""DMS core tables — initial Postgres schema (A1/A2).

Revision ID: 001_dms_core
Revises:
Create Date: 2026-08-04
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "001_dms_core"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS catalog_parts (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            make TEXT DEFAULT '',
            model TEXT DEFAULT '',
            year TEXT DEFAULT '',
            category TEXT DEFAULT '',
            oem_brand TEXT DEFAULT '',
            list_price DOUBLE PRECISION DEFAULT 0,
            msrp DOUBLE PRECISION DEFAULT 0,
            source TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS inventory_levels (
            sku TEXT NOT NULL REFERENCES catalog_parts(sku),
            location_id INTEGER NOT NULL REFERENCES locations(id),
            qty INTEGER NOT NULL DEFAULT 0,
            cost DOUBLE PRECISION DEFAULT 0,
            price DOUBLE PRECISION DEFAULT 0,
            CONSTRAINT uq_inventory_sku_loc UNIQUE (sku, location_id)
        );

        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            company TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS order_lines (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            sku TEXT NOT NULL REFERENCES catalog_parts(sku),
            location_id INTEGER NOT NULL REFERENCES locations(id),
            qty INTEGER NOT NULL,
            unit_price DOUBLE PRECISION NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS oem_sync_runs (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            parts_upserted INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'running',
            message TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_levels(sku);
        CREATE INDEX IF NOT EXISTS idx_inventory_loc ON inventory_levels(location_id);
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
        CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS order_lines CASCADE;
        DROP TABLE IF EXISTS orders CASCADE;
        DROP TABLE IF EXISTS oem_sync_runs CASCADE;
        DROP TABLE IF EXISTS inventory_levels CASCADE;
        DROP TABLE IF EXISTS catalog_parts CASCADE;
        DROP TABLE IF EXISTS customers CASCADE;
        DROP TABLE IF EXISTS locations CASCADE;
        """
    )
