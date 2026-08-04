"""Run Alembic migrations for DMS Postgres schema."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


def monorepo_root() -> Path:
    # src/parrts/dms/migrate.py → parents[3] = monorepo root
    return Path(__file__).resolve().parents[3]


def run_alembic(args: list[str], *, database_url: str | None = None) -> dict[str, Any]:
    """
    Invoke alembic CLI against repo alembic.ini.

    Returns dict with ok, returncode, stdout, stderr.
    """
    root = monorepo_root()
    ini = root / "alembic.ini"
    if not ini.is_file():
        return {"ok": False, "error": f"alembic.ini not found at {ini}"}

    cmd = [sys.executable, "-m", "alembic", "-c", str(ini), *args]
    env = None
    if database_url:
        import os

        env = os.environ.copy()
        env["DMS_DATABASE_URL"] = database_url
        env.setdefault("DMS_BACKEND", "postgres")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "error": f"alembic not available: {exc}"}

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "cmd": cmd,
    }


def upgrade_head(database_url: str | None = None) -> dict[str, Any]:
    return run_alembic(["upgrade", "head"], database_url=database_url)


def current(database_url: str | None = None) -> dict[str, Any]:
    return run_alembic(["current"], database_url=database_url)
