"""DMS backend selection: sqlite (default) | postgres."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

BackendName = Literal["sqlite", "postgres"]


@dataclass(frozen=True)
class DmsBackendConfig:
    backend: BackendName
    database_url: str | None = None
    root: Path | None = None

    @property
    def label(self) -> str:
        if self.backend == "sqlite":
            root = self.root or Path(".")
            return f"sqlite:{root / '.parrts' / 'dms.db'}"
        return f"postgres:{_redact_url(self.database_url or '')}"


def _redact_url(url: str) -> str:
    if not url or "@" not in url:
        return url or ""
    try:
        head, tail = url.split("@", 1)
        if "://" in head:
            scheme, creds = head.split("://", 1)
            user = creds.split(":", 1)[0] if creds else ""
            return f"{scheme}://{user}:***@{tail}"
    except Exception:  # noqa: BLE001
        return "***"
    return "***"


def build_postgres_url_from_env() -> str | None:
    """Build a SQLAlchemy/psycopg2 URL from DMS_DATABASE_URL, DATABASE_URL, or POSTGRES_*."""
    explicit = (
        os.environ.get("DMS_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or ""
    ).strip()
    if explicit:
        # Normalize postgres:// → postgresql:// for SQLAlchemy
        if explicit.startswith("postgres://"):
            explicit = "postgresql://" + explicit[len("postgres://") :]
        return explicit

    host = os.environ.get("POSTGRES_HOST", "").strip()
    if not host:
        return None
    port = os.environ.get("POSTGRES_PORT", "5432").strip() or "5432"
    db = os.environ.get("POSTGRES_DB", "dealership_parts").strip() or "dealership_parts"
    user = os.environ.get("POSTGRES_USER", "postgres").strip() or "postgres"
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{db}"
    )


def resolve_backend(
    *,
    backend: str | None = None,
    database_url: str | None = None,
    root: Path | str | None = None,
) -> DmsBackendConfig:
    """
    Resolve DMS backend.

    Env:
      DMS_BACKEND=sqlite|postgres  (default sqlite)
      DMS_DATABASE_URL / DATABASE_URL / POSTGRES_* for postgres
    """
    name = (backend or os.environ.get("DMS_BACKEND") or "sqlite").strip().lower()
    if name in {"pg", "postgresql", "psycopg", "psycopg2"}:
        name = "postgres"
    if name not in {"sqlite", "postgres"}:
        raise ValueError(f"Unsupported DMS_BACKEND={name!r} (use sqlite|postgres)")

    root_path = Path(root).resolve() if root is not None else None
    if name == "sqlite":
        return DmsBackendConfig(backend="sqlite", database_url=None, root=root_path)

    url = (database_url or build_postgres_url_from_env() or "").strip() or None
    if not url:
        raise ValueError(
            "DMS_BACKEND=postgres requires DMS_DATABASE_URL, DATABASE_URL, "
            "or POSTGRES_HOST (+ POSTGRES_DB/USER/PASSWORD)"
        )
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return DmsBackendConfig(backend="postgres", database_url=url, root=root_path)


def open_store(config: DmsBackendConfig, root: Path | str):
    """Open the concrete store for config."""
    from parrts.dms.store import DmsStore

    if config.backend == "sqlite":
        return DmsStore(root)
    from parrts.dms.pg_store import PostgresDmsStore

    assert config.database_url
    return PostgresDmsStore(root=root, database_url=config.database_url)
