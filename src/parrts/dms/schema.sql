-- DMS core schema (SQLite + Postgres compatible shapes)
-- SQLite uses AUTOINCREMENT; Postgres migration uses SERIAL / IDENTITY.

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

CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_levels(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_loc ON inventory_levels(location_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_supersession_old ON part_supersessions(old_sku);
CREATE INDEX IF NOT EXISTS idx_payment_events_order ON payment_events(order_id);
