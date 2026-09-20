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

-- ============================================================
-- Transmission Hard-Parts Vertical (non-destructive extension)
-- ============================================================

-- Transmission families (data-driven, not enum)
CREATE TABLE IF NOT EXISTS transmission_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family TEXT NOT NULL UNIQUE,           -- e.g. "6L80", "10R80", "68RFE"
    manufacturer TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

-- Extended identifiers / aliases for catalog parts
CREATE TABLE IF NOT EXISTS part_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    identifier_type TEXT NOT NULL,         -- oem, casting, aftermarket, common_name, abbreviation
    identifier_value TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (sku, identifier_type, identifier_value),
    FOREIGN KEY (sku) REFERENCES catalog_parts(sku)
);

-- Interchange relationships (directional)
CREATE TABLE IF NOT EXISTS part_interchanges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_sku TEXT NOT NULL,
    target_sku TEXT NOT NULL,
    relationship_type TEXT NOT NULL,       -- interchangeable, supersedes, core_exchange, not_interchangeable
    confidence REAL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    source TEXT DEFAULT '',                -- provenance / verification source
    verification_status TEXT DEFAULT 'unverified', -- unverified | verified | disputed
    created_at TEXT NOT NULL,
    actor TEXT DEFAULT '',
    UNIQUE (source_sku, target_sku, relationship_type),
    FOREIGN KEY (source_sku) REFERENCES catalog_parts(sku),
    FOREIGN KEY (target_sku) REFERENCES catalog_parts(sku)
);

-- Minimal fitment table (for transmission vertical)
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

-- Extend catalog_parts with transmission-specific identity fields
ALTER TABLE catalog_parts ADD COLUMN transmission_family TEXT DEFAULT '';
ALTER TABLE catalog_parts ADD COLUMN transmission_variant TEXT DEFAULT '';
ALTER TABLE catalog_parts ADD COLUMN verification_status TEXT DEFAULT 'unverified';

-- Extend inventory_levels with condition (new/used/rebuilt/core)
ALTER TABLE inventory_levels ADD COLUMN condition TEXT DEFAULT 'new';

-- Indexes for new transmission tables
CREATE INDEX IF NOT EXISTS idx_part_identifiers_sku ON part_identifiers(sku);
CREATE INDEX IF NOT EXISTS idx_part_interchanges_source ON part_interchanges(source_sku);
CREATE INDEX IF NOT EXISTS idx_part_interchanges_target ON part_interchanges(target_sku);
CREATE INDEX IF NOT EXISTS idx_part_fitments_sku ON part_fitments(sku);
CREATE INDEX IF NOT EXISTS idx_catalog_transmission ON catalog_parts(transmission_family);

-- Ensure bin column exists on existing databases
ALTER TABLE inventory_levels ADD COLUMN bin TEXT DEFAULT NULL;
