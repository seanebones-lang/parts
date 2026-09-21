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
    bin TEXT DEFAULT NULL,
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

CREATE TABLE IF NOT EXISTS notification_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    kind TEXT NOT NULL DEFAULT 'order_status',
    channel TEXT NOT NULL DEFAULT 'email',
    to_address TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'drafted',
    dry_run INTEGER NOT NULL DEFAULT 1,
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

-- Transmission Hard-Parts Vertical (non-destructive extension)
CREATE TABLE IF NOT EXISTS transmission_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family TEXT NOT NULL UNIQUE,
    manufacturer TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS part_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (sku, identifier_type, identifier_value),
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku)
);

CREATE TABLE IF NOT EXISTS part_interchanges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_sku TEXT NOT NULL,
    target_sku TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    source TEXT DEFAULT '',
    verification_status TEXT DEFAULT 'unverified',
    created_at TEXT NOT NULL,
    actor TEXT DEFAULT '',
    UNIQUE (source_sku, target_sku, relationship_type),
    FOREIGN KEY (source_sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (target_sku) REFERENCES catalog_parts(sku)
);

CREATE TABLE IF NOT EXISTS part_fitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    year_from INTEGER,
    year_to INTEGER,
    make TEXT,
    model TEXT,
    engine TEXT,
    transmission_family TEXT,
    transmission_variant TEXT,
    notes TEXT DEFAULT '',
    verification_status TEXT DEFAULT 'unverified',
    created_at TEXT NOT NULL,
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku)
);

-- Extend catalog_parts / inventory via soft-add in ensure_schema()
-- (unconditional ALTER TABLE is not idempotent on SQLite)

CREATE INDEX IF NOT EXISTS idx_part_identifiers_sku ON part_identifiers(sku);
CREATE INDEX IF NOT EXISTS idx_part_interchanges_source ON part_interchanges(source_sku);
CREATE INDEX IF NOT EXISTS idx_part_fitments_sku ON part_fitments(sku);
CREATE INDEX IF NOT EXISTS idx_shipment_events_order ON shipment_events(order_id);
CREATE INDEX IF NOT EXISTS idx_notification_events_order ON notification_events(order_id);
CREATE INDEX IF NOT EXISTS idx_notification_events_created ON notification_events(created_at);
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
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise
        for col_sql in (
            "ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN last_payment_id TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN paid_amount REAL DEFAULT 0",
            "ALTER TABLE orders ADD COLUMN ship_status TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN tracking_code TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN last_shipment_id TEXT DEFAULT ''",
            # Transmission vertical extensions (idempotent soft-add)
            "ALTER TABLE catalog_parts ADD COLUMN transmission_family TEXT DEFAULT ''",
            "ALTER TABLE catalog_parts ADD COLUMN transmission_variant TEXT DEFAULT ''",
            "ALTER TABLE catalog_parts ADD COLUMN verification_status TEXT DEFAULT 'unverified'",
            "ALTER TABLE inventory_levels ADD COLUMN condition TEXT DEFAULT 'new'",
            "ALTER TABLE inventory_levels ADD COLUMN bin TEXT DEFAULT NULL",
            "ALTER TABLE inventory_levels ADD COLUMN reserved_qty INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE orders ADD COLUMN quote_id INTEGER",
            "ALTER TABLE orders ADD COLUMN order_number TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN customer_label TEXT DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN actor TEXT DEFAULT ''",
        ):
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError as exc:
                # Column already present on upgraded DBs — expected and safe.
                if "duplicate column" not in str(exc).lower():
                    raise
        # Operational core: events, quotes, reservations
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS inventory_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                sku TEXT NOT NULL,
                location_id INTEGER,
                qty_on_hand_delta INTEGER NOT NULL DEFAULT 0,
                qty_reserved_delta INTEGER NOT NULL DEFAULT 0,
                on_hand_before INTEGER NOT NULL DEFAULT 0,
                on_hand_after INTEGER NOT NULL DEFAULT 0,
                reserved_before INTEGER NOT NULL DEFAULT 0,
                reserved_after INTEGER NOT NULL DEFAULT 0,
                reason TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                actor TEXT DEFAULT '',
                ref_type TEXT DEFAULT '',
                ref_id TEXT DEFAULT '',
                idempotency_key TEXT UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_inv_events_sku ON inventory_events(sku);
            CREATE INDEX IF NOT EXISTS idx_inv_events_created ON inventory_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_inv_events_type ON inventory_events(event_type);

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_number TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'draft',
                customer_label TEXT NOT NULL DEFAULT '',
                customer_contact TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                actor TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);

            CREATE TABLE IF NOT EXISTS quote_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                location_id INTEGER NOT NULL,
                qty INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL DEFAULT 0,
                description TEXT DEFAULT '',
                FOREIGN KEY (quote_id) REFERENCES quotes(id),
                FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_quote_lines_quote ON quote_lines(quote_id);

            CREATE TABLE IF NOT EXISTS inventory_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                location_id INTEGER NOT NULL,
                qty INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                quote_id INTEGER,
                quote_line_id INTEGER,
                order_id INTEGER,
                actor TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                idempotency_key TEXT UNIQUE,
                created_at TEXT NOT NULL,
                released_at TEXT,
                FOREIGN KEY (sku) REFERENCES catalog_parts(sku),
                FOREIGN KEY (location_id) REFERENCES locations(id),
                FOREIGN KEY (quote_id) REFERENCES quotes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_reservations_status ON inventory_reservations(status);
            CREATE INDEX IF NOT EXISTS idx_reservations_sku ON inventory_reservations(sku);
            """
        )
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
