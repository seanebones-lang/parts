"""SQLite + FTS5 persistence for inbound email desk (stdlib only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

# Keep SQL lines short for ruff E501
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL UNIQUE,
    thread_id TEXT,
    subject TEXT NOT NULL DEFAULT '',
    sender_email TEXT NOT NULL DEFAULT '',
    sender_name TEXT DEFAULT '',
    recipient_email TEXT NOT NULL DEFAULT 'parts@dealership.local',
    body_text TEXT NOT NULL DEFAULT '',
    body_html TEXT DEFAULT '',
    received_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    email_type TEXT,
    priority TEXT DEFAULT 'medium',
    department TEXT DEFAULT 'parts',
    classification_confidence REAL,
    traffic_light TEXT,
    traffic_confidence REAL,
    traffic_reason TEXT,
    requires_human INTEGER NOT NULL DEFAULT 1,
    specialist TEXT,
    suggested_response TEXT,
    extracted_json TEXT DEFAULT '{}',
    hits_json TEXT DEFAULT '[]',
    actions_json TEXT DEFAULT '[]',
    agents_invoked_json TEXT DEFAULT '[]',
    ai_processed INTEGER NOT NULL DEFAULT 0,
    response_sent INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_tl ON emails(traffic_light);
CREATE INDEX IF NOT EXISTS idx_emails_type ON emails(email_type);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender_email);
CREATE INDEX IF NOT EXISTS idx_emails_received ON emails(received_at);

CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
    message_id,
    subject,
    sender_email,
    sender_name,
    body_text,
    suggested_response,
    content='emails',
    content_rowid='id'
);
"""

# Triggers split to stay under line-length
_TRIGGERS = [
    """
CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
  INSERT INTO emails_fts(
    rowid, message_id, subject, sender_email, sender_name,
    body_text, suggested_response
  ) VALUES (
    new.id, new.message_id, new.subject, new.sender_email, new.sender_name,
    new.body_text, new.suggested_response
  );
END;
""",
    """
CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
  INSERT INTO emails_fts(
    emails_fts, rowid, message_id, subject, sender_email, sender_name,
    body_text, suggested_response
  ) VALUES (
    'delete', old.id, old.message_id, old.subject, old.sender_email,
    old.sender_name, old.body_text, old.suggested_response
  );
END;
""",
    """
CREATE TRIGGER IF NOT EXISTS emails_au AFTER UPDATE ON emails BEGIN
  INSERT INTO emails_fts(
    emails_fts, rowid, message_id, subject, sender_email, sender_name,
    body_text, suggested_response
  ) VALUES (
    'delete', old.id, old.message_id, old.subject, old.sender_email,
    old.sender_name, old.body_text, old.suggested_response
  );
  INSERT INTO emails_fts(
    rowid, message_id, subject, sender_email, sender_name,
    body_text, suggested_response
  ) VALUES (
    new.id, new.message_id, new.subject, new.sender_email, new.sender_name,
    new.body_text, new.suggested_response
  );
END;
""",
]


class EmailStore:
    """Thin SQLite wrapper under ``{root}/.parrts/emails.db``."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.db_path = self.root / ".parrts" / "emails.db"
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
        for trig in _TRIGGERS:
            conn.executescript(trig)
        # Production desk columns (idempotent)
        for col_sql in (
            "ALTER TABLE emails ADD COLUMN human_notes TEXT DEFAULT ''",
            "ALTER TABLE emails ADD COLUMN response_sent_at TEXT",
            "ALTER TABLE emails ADD COLUMN last_send_error TEXT",
            "ALTER TABLE emails ADD COLUMN polished INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE emails ADD COLUMN jev_shadow_json TEXT",
        ):
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass
        conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        return self.connect().execute(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Row | None:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[sqlite3.Row]:
        return list(self.execute(sql, params).fetchall())

    def commit(self) -> None:
        self.connect().commit()
