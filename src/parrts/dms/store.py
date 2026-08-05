"""SQLite persistence for offline DMS (stdlib sqlite3 only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    list_price REAL DEFAULT 0,
    msrp REAL DEFAULT 0,
    source TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS inventory_levels (
    sku TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0,
    cost REAL DEFAULT 0,
    price REAL DEFAULT 0,
    UNIQUE (sku, location_id),
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    company TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    notes TEXT DEFAULT '',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    unit_price REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS oem_sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    parts_upserted INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    message TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS orgs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_location_acl (
    user_key TEXT NOT NULL,
    location_code TEXT NOT NULL,
    UNIQUE (user_key, location_code)
);

CREATE TABLE IF NOT EXISTS stock_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    from_location_id INTEGER NOT NULL,
    to_location_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    requested_by TEXT DEFAULT '',
    approved_by TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (from_location_id) REFERENCES locations(id),
    FOREIGN KEY (to_location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS stock_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    qty_before INTEGER NOT NULL,
    qty_after INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT 'adjust',
    notes TEXT DEFAULT '',
    actor TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS part_supersessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    old_sku TEXT NOT NULL,
    new_sku TEXT NOT NULL,
    effective_from TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    actor TEXT DEFAULT '',
    UNIQUE (old_sku, new_sku),
    FOREIGN KEY (old_sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (new_sku) REFERENCES catalog_parts(sku)
);

CREATE TABLE IF NOT EXISTS payment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    provider TEXT NOT NULL DEFAULT 'stripe',
    external_id TEXT DEFAULT '',
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'usd',
    status TEXT NOT NULL DEFAULT 'created',
    configured INTEGER NOT NULL DEFAULT 0,
    message TEXT DEFAULT '',
    actor TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS shipment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    provider TEXT NOT NULL DEFAULT 'easypost',
    external_id TEXT DEFAULT '',
    tracking_code TEXT DEFAULT '',
    label_url TEXT DEFAULT '',
    carrier TEXT DEFAULT '',
    service TEXT DEFAULT '',
    rate REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'rates',
    configured INTEGER NOT NULL DEFAULT 0,
    message TEXT DEFAULT '',
    actor TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_levels(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_loc ON inventory_levels(location_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_acl_user ON user_location_acl(user_key);
CREATE INDEX IF NOT EXISTS idx_transfers_status ON stock_transfers(status);
CREATE INDEX IF NOT EXISTS idx_adjustments_sku ON stock_adjustments(sku);
CREATE INDEX IF NOT EXISTS idx_adjustments_created ON stock_adjustments(created_at);
CREATE INDEX IF NOT EXISTS idx_supersession_old ON part_supersessions(old_sku);
CREATE INDEX IF NOT EXISTS idx_supersession_new ON part_supersessions(new_sku);
CREATE INDEX IF NOT EXISTS idx_payment_events_order ON payment_events(order_id);
CREATE INDEX IF NOT EXISTS idx_shipment_events_order ON shipment_events(order_id);
"""


class DmsStore:
    """Thin SQLite wrapper for DMS tables under ``{root}/.parrts/dms.db``."""

    backend_name = "sqlite"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.db_path = self.root / ".parrts" / "dms.db"
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def ensure_schema(self) -> None:
        conn = self.connect()
        conn.executescript(SCHEMA_SQL)
        # Soft-add org_id on locations for multi-rooftop (SQLite)
        try:
            conn.execute("ALTER TABLE locations ADD COLUMN org_id INTEGER")
        except Exception:  # noqa: BLE001 — column may already exist
            pass
        for col_sql in (
            "ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN last_payment_id TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN paid_amount REAL DEFAULT 0",
            "ALTER TABLE orders ADD COLUMN ship_status TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN tracking_code TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN last_shipment_id TEXT DEFAULT ''",
        ):
            try:
                conn.execute(col_sql)
            except Exception:  # noqa: BLE001 — column may already exist
                pass
        conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        return self.connect().execute(sql, params)

    def executemany(self, sql: str, seq: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        return self.connect().executemany(sql, seq)

    def commit(self) -> None:
        self.connect().commit()

    def fetchone(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Row | None:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[sqlite3.Row]:
        return list(self.execute(sql, params).fetchall())
