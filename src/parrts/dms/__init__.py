"""Offline DMS core + OEM feed adapters (SQLite default; Postgres optional)."""

from __future__ import annotations

from parrts.dms.backend import DmsBackendConfig, resolve_backend
from parrts.dms.oem import FileOemFeed, HttpOemFeed, OemFeed, SyntheticOemFeed
from parrts.dms.service import DmsService, InsufficientStockError
from parrts.dms.store import DmsStore

__all__ = [
    "DmsBackendConfig",
    "DmsService",
    "DmsStore",
    "InsufficientStockError",
    "OemFeed",
    "SyntheticOemFeed",
    "FileOemFeed",
    "HttpOemFeed",
    "resolve_backend",
]
