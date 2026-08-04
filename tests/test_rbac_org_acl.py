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

def test_oem_schedule_skips_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OEM_FEED_URL", raising=False)
    from app.tasks.oem_tasks import run_scheduled_oem_sync

    out = run_scheduled_oem_sync(root=str(Path.cwd()))
    assert out["skipped"] is True
    assert out["ok"] is True
