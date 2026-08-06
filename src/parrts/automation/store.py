"""SQLite persistence for automation runs + field/error alerts."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS automation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    source_ref TEXT,
    status TEXT NOT NULL DEFAULT 'ok',
    summary TEXT NOT NULL DEFAULT '',
    detail_json TEXT NOT NULL DEFAULT '{}',
    requires_human INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auto_runs_kind ON automation_runs(kind);
CREATE INDEX IF NOT EXISTS idx_auto_runs_status ON automation_runs(status);
CREATE INDEX IF NOT EXISTS idx_auto_runs_created ON automation_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_auto_runs_human ON automation_runs(requires_human);

CREATE TABLE IF NOT EXISTS automation_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    severity TEXT NOT NULL DEFAULT 'yellow',
    code TEXT NOT NULL DEFAULT 'generic',
    message TEXT NOT NULL DEFAULT '',
    fields_json TEXT NOT NULL DEFAULT '[]',
    resolved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES automation_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_auto_alerts_sev ON automation_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_auto_alerts_res ON automation_alerts(resolved);
"""


class AutomationStore:
    """Thin SQLite wrapper under ``{root}/.parrts/automation.db``."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.db_path = self.root / ".parrts" / "automation.db"
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
        conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        return self.connect().execute(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Row | None:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[sqlite3.Row]:
        return list(self.execute(sql, params).fetchall())

    def commit(self) -> None:
        self.connect().commit()
