"""Postgres DMS store — same SQL surface as DmsStore (? → %s, lastval for ids)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Schema DDL for Postgres (SERIAL + explicit UNIQUE name for ON CONFLICT)
PG_SCHEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS orgs (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_location_acl (
    user_key TEXT NOT NULL,
    location_code TEXT NOT NULL,
    CONSTRAINT uq_acl_user_loc UNIQUE (user_key, location_code)
);

CREATE TABLE IF NOT EXISTS stock_transfers (
    id SERIAL PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES catalog_parts(sku),
    from_location_id INTEGER NOT NULL REFERENCES locations(id),
    to_location_id INTEGER NOT NULL REFERENCES locations(id),
    qty INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    requested_by TEXT DEFAULT '',
    approved_by TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_levels(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_loc ON inventory_levels(location_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_acl_user ON user_location_acl(user_key);
CREATE INDEX IF NOT EXISTS idx_transfers_status ON stock_transfers(status);
"""


def _qmark_to_pyformat(sql: str) -> str:
    """Convert sqlite-style ? placeholders to psycopg2 %s (no string-literal awareness needed for our SQL)."""
    return sql.replace("?", "%s")


class _PgRow(dict):
    """dict subclass that also supports sqlite3.Row-style integer and key access."""

    def __getitem__(self, key: Any) -> Any:  # type: ignore[override]
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _CursorProxy:
    def __init__(self, cur: Any) -> None:
        self._cur = cur
        self.lastrowid: int | None = None

    def fetchone(self) -> _PgRow | None:
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description]
        return _PgRow(zip(cols, row))

    def fetchall(self) -> list[_PgRow]:
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cur.description]
        return [_PgRow(zip(cols, r)) for r in rows]


class PostgresDmsStore:
    """Thin psycopg2 wrapper matching DmsStore methods used by DmsService."""

    def __init__(self, root: Path | str, database_url: str) -> None:
        self.root = Path(root).resolve()
        self.database_url = database_url
        # status() expects db_path-like field
        self.db_path = f"postgres:{database_url.split('@')[-1] if '@' in database_url else 'configured'}"
        self._conn: Any = None

    def connect(self) -> Any:
        if self._conn is None:
            try:
                import psycopg2
                from psycopg2.extensions import connection as PgConnection
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "psycopg2 is required for DMS_BACKEND=postgres "
                    "(pip install 'parrts[postgres]' or psycopg2-binary)"
                ) from exc
            # SQLAlchemy-style postgresql:// works with psycopg2 if we strip +driver
            url = self.database_url
            if url.startswith("postgresql+psycopg2://"):
                url = "postgresql://" + url[len("postgresql+psycopg2://") :]
            elif url.startswith("postgresql+psycopg://"):
                url = "postgresql://" + url[len("postgresql+psycopg://") :]
            self._conn = psycopg2.connect(url)
            assert isinstance(self._conn, PgConnection)
            self._conn.autocommit = False
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def ensure_schema(self) -> None:
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(PG_SCHEMA_SQL)
            try:
                cur.execute(
                    "ALTER TABLE locations ADD COLUMN IF NOT EXISTS org_id INTEGER"
                )
            except Exception:  # noqa: BLE001
                pass
        conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> _CursorProxy:
        conn = self.connect()
        cur = conn.cursor()
        pg_sql = _qmark_to_pyformat(sql)
        cur.execute(pg_sql, tuple(params))
        proxy = _CursorProxy(cur)
        # Mirror sqlite3 lastrowid for INSERT into SERIAL tables
        stripped = sql.lstrip().upper()
        if stripped.startswith("INSERT") and "RETURNING" not in stripped:
            try:
                cur2 = conn.cursor()
                cur2.execute("SELECT LASTVAL()")
                row = cur2.fetchone()
                cur2.close()
                if row is not None:
                    proxy.lastrowid = int(row[0])
            except Exception:  # noqa: BLE001 — non-serial inserts (e.g. catalog sku PK)
                proxy.lastrowid = None
        return proxy

    def executemany(self, sql: str, seq: list[tuple[Any, ...]]) -> _CursorProxy:
        conn = self.connect()
        cur = conn.cursor()
        cur.executemany(_qmark_to_pyformat(sql), seq)
        return _CursorProxy(cur)

    def commit(self) -> None:
        self.connect().commit()

    def fetchone(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> _PgRow | None:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[_PgRow]:
        return self.execute(sql, params).fetchall()
