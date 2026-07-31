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
    from app.api import deps
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    assert deps._is_demo_mode() is True

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    assert deps._is_demo_mode() is False

    monkeypatch.setattr(settings, "AUTH_MODE", "DEMO")
    assert deps._is_demo_mode() is True


@pytest.mark.asyncio
async def test_require_user_demo_allows_missing_bearer(monkeypatch):
    from app.api.deps import require_user_if_production
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    result = await require_user_if_production(credentials=None)
    assert result is None


@pytest.mark.asyncio
async def test_require_user_production_rejects_missing_bearer(monkeypatch):
    from app.api.deps import require_user_if_production
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    with pytest.raises(HTTPException) as ei:
        await require_user_if_production(credentials=None)
    assert ei.value.status_code == 401
    assert ei.value.headers and ei.value.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_require_user_production_invalid_token_401(monkeypatch):
    from app.api.deps import require_user_if_production
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

    async def _fake_get_db():
        yield MagicMock()

    with patch("app.api.deps.get_db", _fake_get_db):
        with patch("app.api.deps.AuthService") as MockAuth:
            inst = MockAuth.return_value
            inst.verify_token.return_value = None
            with pytest.raises(HTTPException) as ei:
                await require_user_if_production(credentials=creds)
            assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_require_user_demo_invalid_token_returns_none(monkeypatch):
    from app.api.deps import require_user_if_production
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
    # Demo mode ignores tokens and never opens DB
    result = await require_user_if_production(credentials=creds)
    assert result is None


@pytest.mark.asyncio
async def test_require_user_production_valid_token_returns_user(monkeypatch):
    from app.api.deps import require_user_if_production
    from app.core.config import settings

    monkeypatch.setattr(settings, "AUTH_MODE", "production")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good-token")
    fake_user = MagicMock()
    fake_user.id = 42

    async def _fake_get_db():
        yield MagicMock()

    with patch("app.api.deps.get_db", _fake_get_db):
        with patch("app.api.deps.AuthService") as MockAuth:
            inst = MockAuth.return_value
            inst.verify_token.return_value = {"sub": "42"}
            inst.get_user_by_id = AsyncMock(return_value=fake_user)
            result = await require_user_if_production(credentials=creds)
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

    from app.api.v1.endpoints import orders, parts

    for fn in (
        parts.bulk_import_parts,
        parts.index_part_for_search,
        orders.create_order,
        orders.update_order_status,
        orders.cancel_order,
        orders.create_invoice,
    ):
        src = inspect.getsource(fn)
        assert "require_user_if_production" in src
        assert "current_user" in src


def test_inventory_payments_customers_mutating_wire_require_user():
    """Pattern check: inventory/payments/customers mutating handlers use gate."""
    import inspect
    import re

    from app.api.v1.endpoints import customers, inventory, payments

    modules = {
        "inventory": inventory,
        "payments": payments,
        "customers": customers,
    }
    # Provider webhooks stay signature-auth only (no JWT gate)
    skip_fns = {"handle_stripe_webhook"}

    checked = 0
    for mod_name, mod in modules.items():
        for fn_name, fn in inspect.getmembers(mod, inspect.iscoroutinefunction):
            if fn_name in skip_fns:
                continue
            if getattr(fn, "__module__", None) != mod.__name__:
                continue
            try:
                src = inspect.getsource(fn)
            except OSError:
                continue
            # inspect.getsource includes the decorator line(s)
            if not re.search(r"@router\.(post|put|delete|patch)\b", src):
                continue
            assert "require_user_if_production" in src, (
                f"{mod_name}.{fn_name} missing require_user_if_production"
            )
            assert "current_user" in src, f"{mod_name}.{fn_name} missing current_user"
            checked += 1

    assert checked >= 10, f"expected many mutating handlers wired, got {checked}"


def test_stripe_webhook_not_jwt_gated():
    import inspect

    from app.api.v1.endpoints import payments

    src = inspect.getsource(payments.handle_stripe_webhook)
    # Docstring may mention the helper name; the Depends() wire must be absent.
    assert "Depends(require_user_if_production)" not in src
    assert "current_user" not in src.split('"""')[-1]  # body after docstring
    assert "signature" in src.lower() or "stripe-signature" in src.lower()


def test_settings_auth_mode_default():
    from app.core.config import settings

    assert settings.AUTH_MODE in {"demo", "production"}


def test_secret_key_is_insecure_helper():
    from app.core.config import Settings

    s = Settings(
        SECRET_KEY="your-secret-key-change-in-production",
        ENVIRONMENT="development",
        AUTH_MODE="demo",
        DEBUG=True,
    )
    assert s.secret_key_is_insecure() is True

    s2 = Settings(
        SECRET_KEY="secret",
        ENVIRONMENT="development",
        AUTH_MODE="demo",
        DEBUG=True,
    )
    assert s2.secret_key_is_insecure() is True

    s3 = Settings(
        SECRET_KEY="",
        ENVIRONMENT="development",
        AUTH_MODE="demo",
        DEBUG=True,
    )
    assert s3.secret_key_is_insecure() is True

    s4 = Settings(
        SECRET_KEY="a-long-enough-unique-production-secret-key-99",
        ENVIRONMENT="development",
        AUTH_MODE="demo",
        DEBUG=True,
    )
    assert s4.secret_key_is_insecure() is False


def test_is_production_runtime():
    from app.core.config import Settings

    assert (
        Settings(
            ENVIRONMENT="production", AUTH_MODE="demo", DEBUG=False, SECRET_KEY="x" * 40
        ).is_production_runtime()
        is True
    )
    assert (
        Settings(
            ENVIRONMENT="development",
            AUTH_MODE="production",
            DEBUG=False,
            SECRET_KEY="x" * 40,
        ).is_production_runtime()
        is True
    )
    assert (
        Settings(
            ENVIRONMENT="development", AUTH_MODE="demo", DEBUG=True, SECRET_KEY="x" * 40
        ).is_production_runtime()
        is False
    )
