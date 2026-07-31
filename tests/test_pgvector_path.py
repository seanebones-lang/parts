"""Offline unit tests for pgvector path configuration (no live DB required)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vector_service_has_pgvector_status_method():
    src = (ROOT / "backend" / "app" / "services" / "vector_service.py").read_text(
        encoding="utf-8"
    )
    assert "def backend_status" in src or "def pgvector_status" in src
    assert "PGVECTOR" in src or "pgvector" in src.lower()
    # Safety: still whitelist filters
    assert "_FILTER_EQ_COLUMNS" in src


def test_settings_exposes_pgvector_flag():
    src = (ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    assert "PGVECTOR_ENABLED" in src
    tree = ast.parse(src)
    assert tree is not None


def test_compose_has_pgvector_profile_or_image():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "pgvector" in compose.lower()
    # profiles optional but preferred
    assert "profiles:" in compose or "pgvector/pgvector" in compose
