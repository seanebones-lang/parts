"""AUTH_MODE demo vs production — require_user_if_production / get_optional_user.

Skipped when enterprise backend extras are not installed so core pytest stays green.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def test_deps_module_exports():
    from app.api import deps

    assert callable(deps.require_user_if_production)
    assert callable(deps.get_optional_user)
    assert callable(deps._is_demo_mode)


def test_is_demo_mode_respects_settings(monkeypatch):
    from app.core.config import settings
    from app.api import deps

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    assert deps._is_demo_mode() is True

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    assert deps._is_demo_mode() is False

    monkeypatch.setattr(settings, "AUTH_MODE", "DEMO")
    assert deps._is_demo_mode() is True


@pytest.mark.asyncio
async def test_require_user_demo_allows_missing_bearer(monkeypatch):
    from app.core.config import settings
    from app.api.deps import require_user_if_production

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    result = await require_user_if_production(credentials=None, db=MagicMock())
    assert result is None


@pytest.mark.asyncio
async def test_require_user_production_rejects_missing_bearer(monkeypatch):
    from app.core.config import settings
    from app.api.deps import require_user_if_production

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    with pytest.raises(HTTPException) as ei:
        await require_user_if_production(credentials=None, db=MagicMock())
    assert ei.value.status_code == 401
    assert ei.value.headers and ei.value.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_require_user_production_invalid_token_401(monkeypatch):
    from app.core.config import settings
    from app.api.deps import require_user_if_production

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

    with patch("app.api.deps.AuthService") as MockAuth:
        inst = MockAuth.return_value
        inst.verify_token.return_value = None
        with pytest.raises(HTTPException) as ei:
            await require_user_if_production(credentials=creds, db=MagicMock())
        assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_require_user_demo_invalid_token_returns_none(monkeypatch):
    from app.core.config import settings
    from app.api.deps import require_user_if_production

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

    with patch("app.api.deps.AuthService") as MockAuth:
        inst = MockAuth.return_value
        inst.verify_token.return_value = None
        result = await require_user_if_production(credentials=creds, db=MagicMock())
        assert result is None


@pytest.mark.asyncio
async def test_require_user_production_valid_token_returns_user(monkeypatch):
    from app.core.config import settings
    from app.api.deps import require_user_if_production

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good-token")
    fake_user = MagicMock()
    fake_user.id = 42

    with patch("app.api.deps.AuthService") as MockAuth:
        inst = MockAuth.return_value
        inst.verify_token.return_value = {"sub": "42"}
        inst.get_user_by_id = AsyncMock(return_value=fake_user)
        result = await require_user_if_production(credentials=creds, db=MagicMock())
        assert result is fake_user
        inst.get_user_by_id.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_get_optional_user_no_creds():
    from app.api.deps import get_optional_user

    assert await get_optional_user(credentials=None, db=MagicMock()) is None


@pytest.mark.asyncio
async def test_get_optional_user_valid():
    from app.api.deps import get_optional_user

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    fake_user = MagicMock()
    with patch("app.api.deps.AuthService") as MockAuth:
        inst = MockAuth.return_value
        inst.verify_token.return_value = {"sub": "7"}
        inst.get_user_by_id = AsyncMock(return_value=fake_user)
        result = await get_optional_user(credentials=creds, db=MagicMock())
        assert result is fake_user


def test_write_endpoints_wire_require_user_if_production():
    """Pattern check: parts + orders mutating routes depend on demo-aware helper."""
    import inspect

    from app.api.v1.endpoints import parts, orders

    for fn in (
        parts.bulk_import_parts,
        parts.index_part_for_search,
        orders.create_order,
    ):
        src = inspect.getsource(fn)
        assert "require_user_if_production" in src
        assert "current_user" in src


def test_settings_auth_mode_default():
    from app.core.config import settings

    assert settings.AUTH_MODE in {"demo", "production"}
