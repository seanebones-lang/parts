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

CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_levels(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_loc ON inventory_levels(location_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_acl_user ON user_location_acl(user_key);
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
