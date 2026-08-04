"""Unit tests for DMS dual-mode backend selection + SQLite path."""

from __future__ import annotations

from pathlib import Path

import pytest

from parrts.dms.backend import build_postgres_url_from_env, resolve_backend
from parrts.dms.pg_store import _qmark_to_pyformat
from parrts.dms.service import DmsService


def test_qmark_conversion() -> None:
    assert _qmark_to_pyformat("SELECT * FROM t WHERE a = ? AND b = ?") == (
        "SELECT * FROM t WHERE a = %s AND b = %s"
    )


def test_resolve_backend_default_sqlite(tmp_path: Path) -> None:
    cfg = resolve_backend(root=tmp_path)
    assert cfg.backend == "sqlite"


def test_resolve_backend_postgres_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DMS_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.setenv("DMS_BACKEND", "postgres")
    with pytest.raises(ValueError, match="DMS_DATABASE_URL"):
        resolve_backend(backend="postgres")


def test_build_url_from_postgres_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DMS_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "db.example")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "parts")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss")
    url = build_postgres_url_from_env()
    assert url is not None
    assert url.startswith("postgresql://")
    assert "db.example:5433/parts" in url
    assert "p%40ss" in url  # quoted


def test_sqlite_service_status_includes_backend(tmp_path: Path) -> None:
    svc = DmsService(root=tmp_path, backend="sqlite")
    st = svc.status()
    assert st["ok"] is True
    assert st["backend"] == "sqlite"
    assert st["locations"] >= 1


def test_sqlite_seed_still_works(tmp_path: Path) -> None:
    svc = DmsService(root=tmp_path, backend="sqlite")
    out = svc.seed_demo(n_skus=5, locations=2)
    assert out["ok"] is True
    assert out["parts_upserted"] == 5
    st = svc.status()
    assert st["catalog_parts"] == 5
