"""RBAC dependency + org/location ACL tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "backend"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from parrts.dms.service import DmsService
from parrts.rbac import map_app_role, role_from_claims, role_from_user


def test_role_aliases_and_claims() -> None:
    assert map_app_role("user") == "counter"
    assert map_app_role("superuser") == "admin"
    assert role_from_claims({"role": "manager"}) == "manager"
    assert role_from_claims({"parts_role": "admin"}) == "admin"
    u = MagicMock()
    u.is_superuser = True
    u.role = "user"
    assert role_from_user(u) == "admin"
    u.is_superuser = False
    u.role = "manager"
    assert role_from_user(u) == "manager"


def test_org_and_location_acl(tmp_path: Path) -> None:
    dms = DmsService(root=tmp_path)
    dms.ensure_schema()
    org = dms.ensure_org("CHI", "Chicago Group")
    assert org["code"] == "CHI"
    dms.set_location_org("CHI-N", "CHI")
    locs = dms.list_locations()
    chi = next(loc for loc in locs if loc["code"] == "CHI-N")
    assert int(chi["org_id"]) == int(org["id"])

    dms.seed_demo(n_skus=3, locations=2)
    dms.set_user_location_acl("counter1", ["CHI-N"])
    allowed = dms.allowed_location_codes("counter1")
    assert allowed == ["CHI-N"]
    filt = dms.filter_inventory_for_user("counter1")
    assert filt
    assert all(r["location_code"] == "CHI-N" for r in filt)
    # unrestricted user
    all_rows = dms.filter_inventory_for_user(None)
    assert len(all_rows) >= len(filt)


def test_require_permission_demo_role_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Needs backend stack (sqlalchemy); skipped on core CI job."""
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("fastapi")
    import asyncio

    from app.api.deps import require_permission
    from app.core.config import settings
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "AUTH_MODE", "demo")
    dep = require_permission("dms.seed")

    async def _run() -> None:
        with pytest.raises(HTTPException) as ei:
            await dep(credentials=None, x_parts_role="counter")
        assert ei.value.status_code == 403
        user = await dep(credentials=None, x_parts_role="admin")
        assert user is None

    asyncio.run(_run())


def test_jwt_access_token_mints_role_claims() -> None:
    """Wave 22: login/refresh mint role + parts_role via map_app_role."""
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("jose")
    from app.core.config import settings
    from app.services.auth_service import AuthService
    from jose import jwt

    cases = [
        ("user", False, "user", "counter"),
        ("manager", False, "manager", "manager"),
        ("admin", False, "admin", "admin"),
        ("superuser", False, "superuser", "admin"),
        ("user", True, "superuser", "admin"),  # is_superuser wins
    ]
    for app_role, is_super, expect_role, expect_parts in cases:
        u = MagicMock()
        u.id = 7
        u.role = app_role
        u.is_superuser = is_super
        claims = AuthService.access_token_claims_for_user(u)
        assert claims["sub"] == "7"
        assert claims["role"] == expect_role
        assert claims["parts_role"] == expect_parts
        assert claims["is_superuser"] is is_super

        svc = AuthService(db=MagicMock())  # type: ignore[arg-type]
        token = svc.create_access_token_for_user(u)
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "7"
        assert decoded["role"] == expect_role
        assert decoded["parts_role"] == expect_parts

def test_require_permission_production_counter_jwt_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production: counter JWT cannot dms.seed or catalog.import."""
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("fastapi")
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.api.deps import require_permission
    from app.core.config import settings
    from app.services.auth_service import AuthService
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    monkeypatch.setattr(settings, "AUTH_MODE", "production")

    counter = MagicMock()
    counter.id = 11
    counter.role = "user"
    counter.is_superuser = False
    counter.is_active = True

    svc = AuthService(db=MagicMock())  # type: ignore[arg-type]
    token = svc.create_access_token_for_user(counter)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    async def _fake_get_db():
        yield MagicMock()

    async def _run() -> None:
        with patch("app.api.deps.get_db", _fake_get_db):
            with patch("app.api.deps.AuthService") as MockAuth:
                inst = MockAuth.return_value
                # Real verify so claims (role/parts_role) attach to user
                inst.verify_token.side_effect = lambda t: AuthService(MagicMock()).verify_token(t)
                inst.get_user_by_id = AsyncMock(return_value=counter)

                for perm in ("dms.seed", "catalog.import"):
                    dep = require_permission(perm)
                    with pytest.raises(HTTPException) as ei:
                        await dep(credentials=creds, x_parts_role=None)
                    assert ei.value.status_code == 403, perm
                    assert "counter" in str(ei.value.detail)

                # admin claim path allowed
                admin = MagicMock()
                admin.id = 1
                admin.role = "admin"
                admin.is_superuser = False
                admin.is_active = True
                admin_tok = svc.create_access_token_for_user(admin)
                admin_creds = HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials=admin_tok
                )
                inst.get_user_by_id = AsyncMock(return_value=admin)
                ok = await require_permission("dms.seed")(
                    credentials=admin_creds, x_parts_role=None
                )
                assert ok is admin

    asyncio.run(_run())


def test_oem_schedule_skips_without_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pytest.importorskip("sqlalchemy")  # app.tasks import chain
    monkeypatch.delenv("OEM_FEED_URL", raising=False)
    from app.tasks.oem_tasks import run_scheduled_oem_sync

    out = run_scheduled_oem_sync(root=str(tmp_path))
    assert out["skipped"] is True
    assert out["ok"] is True


def test_celery_beat_includes_oem_scheduled_sync() -> None:
    """Wave 24: beat_schedule registers oem.scheduled_sync nightly."""
    pytest.importorskip("celery")
    pytest.importorskip("sqlalchemy")
    from app.celery import celery_app

    sched = celery_app.conf.beat_schedule or {}
    assert "oem-scheduled-sync-nightly" in sched
    entry = sched["oem-scheduled-sync-nightly"]
    assert entry["task"] == "oem.scheduled_sync"
    includes = celery_app.conf.include or []
    assert "app.tasks.oem_tasks" in includes
