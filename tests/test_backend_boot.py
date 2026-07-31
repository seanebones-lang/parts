"""Backend boot smoke tests (no live Postgres required).

Skipped automatically when enterprise backend extras are not installed
so core `pip install -e ".[dev]" && pytest` stays offline-green.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SRC = ROOT / "src"
for p in (ROOT, SRC, BACKEND):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

pytest.importorskip("fastapi")
pytest.importorskip("pydantic_settings")
pytest.importorskip("sqlalchemy")


def test_settings_import():
    from app.core.config import settings

    assert settings.VERSION
    assert settings.AUTH_MODE in {"demo", "production"}
    assert hasattr(settings, "PGVECTOR_ENABLED")
    assert callable(settings.secret_key_is_insecure)
    assert callable(settings.is_production_runtime)


def test_production_secret_guard_rejects_insecure_key(monkeypatch):
    import main as main_mod
    from app.core import config as config_mod

    monkeypatch.setattr(config_mod.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config_mod.settings, "AUTH_MODE", "production")
    monkeypatch.setattr(config_mod.settings, "DEBUG", False)
    monkeypatch.setattr(
        config_mod.settings, "SECRET_KEY", "your-secret-key-change-in-production"
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        main_mod.enforce_production_secrets()


def test_production_secret_guard_rejects_debug(monkeypatch):
    import main as main_mod
    from app.core import config as config_mod

    monkeypatch.setattr(config_mod.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config_mod.settings, "AUTH_MODE", "demo")
    monkeypatch.setattr(config_mod.settings, "DEBUG", True)
    monkeypatch.setattr(
        config_mod.settings, "SECRET_KEY", "a-long-enough-unique-production-secret-key-99"
    )
    with pytest.raises(RuntimeError, match="DEBUG"):
        main_mod.enforce_production_secrets()


def test_production_secret_guard_ok_with_strong_key(monkeypatch):
    import main as main_mod
    from app.core import config as config_mod

    monkeypatch.setattr(config_mod.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config_mod.settings, "AUTH_MODE", "production")
    monkeypatch.setattr(config_mod.settings, "DEBUG", False)
    monkeypatch.setattr(
        config_mod.settings, "SECRET_KEY", "a-long-enough-unique-production-secret-key-99"
    )
    main_mod.enforce_production_secrets()  # no raise


def test_demo_mode_allows_default_secret(monkeypatch):
    import main as main_mod
    from app.core import config as config_mod

    monkeypatch.setattr(config_mod.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(config_mod.settings, "AUTH_MODE", "demo")
    monkeypatch.setattr(config_mod.settings, "DEBUG", True)
    monkeypatch.setattr(
        config_mod.settings, "SECRET_KEY", "your-secret-key-change-in-production"
    )
    main_mod.enforce_production_secrets()  # no raise


def test_api_v1_all_routers_load():
    from app.api.v1.api import api_router, router_status

    st = router_status()
    assert st["loaded_count"] >= 13, st
    assert st["failed_count"] == 0, f"router load failures: {st.get('failed')}"
    assert len(api_router.routes) >= 13


def test_main_mounts_core_and_v1():
    import main

    assert main.api_router is not None
    paths = {getattr(r, "path", None) for r in main.app.routes}
    for p in ("/", "/health", "/query", "/metrics"):
        assert p in paths


def test_parrts_engine_via_main_helper():
    import main

    eng = main._get_parrts_engine()
    assert eng is not None
    result = eng.query("oil filter Toyota Camry", use_llm=False, top_k=3)
    data = result.to_dict()
    assert data.get("hits")
    assert data.get("traffic_light")


def test_auth_service_imports_get_db():
    from app.core.database import get_db
    from app.services import auth_service

    assert callable(get_db)
    assert hasattr(auth_service, "get_current_user")


def test_barcode_serialized_no_reserved_metadata_attr():
    from app.models.barcode import BarcodeScan
    from app.models.serialized import SerializedItem, SerializedItemRecall

    assert hasattr(BarcodeScan, "extra_data")
    assert hasattr(SerializedItem, "extra_data")
    # SQLAlchemy reserved name must not be a mapped attr
    assert "metadata" not in BarcodeScan.__mapper__.attrs.keys()
    assert "metadata" not in SerializedItem.__mapper__.attrs.keys()
    # Dual FK to users must not be ambiguous
    assert "initiated_by_user" in SerializedItemRecall.__mapper__.attrs.keys()
    assert "resolved_by_user" in SerializedItemRecall.__mapper__.attrs.keys()
