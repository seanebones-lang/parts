"""pgvector e2e: runs seed + vector search smoke when DATABASE is up; else skips.

Does **not** require live Docker. Offline unit path stays green via skip.

Enable live run:
  docker compose --profile pgvector up -d
  export DATABASE_URL=postgresql://postgres:password@localhost:5432/dealership_parts
  # or rely on POSTGRES_* defaults matching compose
  pytest -q tests/test_pgvector_e2e.py -m pgvector

Related offline unit coverage (always runs): tests/test_pgvector_path.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED_SCRIPT = ROOT / "scripts" / "seed_pgvector.py"

pytestmark = pytest.mark.pgvector


def _dsn_configured() -> bool:
    if (os.environ.get("DATABASE_URL") or "").strip():
        return True
    # POSTGRES_* always has defaults in compose; still try connect probe
    return True


async def _can_connect(timeout: float = 1.5) -> tuple[bool, str]:
    """Return (ok, reason). Never raises."""
    try:
        import asyncpg
    except ImportError:
        return False, "asyncpg_not_installed"

    # Import seed helpers for consistent DSN building
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        # Load seed module without executing main
        import importlib.util

        spec = importlib.util.spec_from_file_location("seed_pgvector", SEED_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        dsn = mod.build_dsn()
        if not dsn:
            return False, "no_dsn"
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=timeout)
        except Exception as exc:
            return False, f"unreachable:{type(exc).__name__}"
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()
        return True, "ok"
    finally:
        pass


def _db_available() -> tuple[bool, str]:
    return asyncio.run(_can_connect())


@pytest.fixture(scope="module")
def db_ready() -> str:
    ok, reason = _db_available()
    if not ok:
        pytest.skip(
            f"pgvector e2e skipped (no live DB): {reason}. "
            "Start with: docker compose --profile pgvector up -d"
        )
    return reason


def test_seed_script_exists():
    """Unit path: seed script present and documents compose profiles (no Docker)."""
    assert SEED_SCRIPT.is_file()
    text = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "asyncpg" in text
    assert "CREATE EXTENSION" in text or "create extension" in text.lower()
    assert "parts_catalog" in text
    # Compose profile docs in help / module docstring
    assert "--profile" in text or "profile pgvector" in text
    assert "PGVECTOR_ENABLED" in text


def test_seed_skips_cleanly_when_forced_bad_host(monkeypatch):
    """Unit path: unreachable host → exit 0 + skipped=true JSON (no Docker needed)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:1/no_such_db")
    monkeypatch.delenv("SEED_PGVECTOR_FORCE", raising=False)
    proc = subprocess.run(
        [sys.executable, str(SEED_SCRIPT), "--timeout", "0.5"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "DATABASE_URL": "postgresql://postgres:password@127.0.0.1:1/no_such_db"},
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    data = json.loads(proc.stdout)
    assert data.get("skipped") is True
    assert data.get("ok") is True
    assert data.get("reason") in {"db_unreachable", "no_database_url", "asyncpg_not_installed"}


def test_seed_and_vector_search_smoke(db_ready: str):
    """Live path: seed rows then cosine distance query returns seed part."""
    proc = subprocess.run(
        [sys.executable, str(SEED_SCRIPT), "--timeout", "3"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    status = json.loads(proc.stdout)
    if status.get("skipped"):
        pytest.skip(f"seed skipped at runtime: {status}")
    assert status.get("ok") is True
    assert status.get("upserted", 0) >= 1
    assert status.get("vector_extension") is True
    assert status.get("embedding_column_ensured") is True

    async def _search() -> list:
        import asyncpg
        import importlib.util

        spec = importlib.util.spec_from_file_location("seed_pgvector", SEED_SCRIPT)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        dsn = mod.build_dsn()
        dim = int(status.get("embedding_dim") or 1536)
        # Reuse same fake embedding as first seed part so cosine ≈ 1
        q = mod._fake_embedding("PGV-SEED-BRK001", dim, zeros=False)
        emb_lit = mod._embedding_literal(q)
        conn = await asyncpg.connect(dsn)
        try:
            rows = await conn.fetch(
                """
                SELECT part_number,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM parts_catalog
                WHERE embedding IS NOT NULL
                  AND part_number LIKE 'PGV-SEED-%'
                ORDER BY embedding <=> $1::vector
                LIMIT 5
                """,
                emb_lit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    rows = asyncio.run(_search())
    assert rows, "expected at least one seeded vector row"
    top = rows[0]
    assert str(top["part_number"]).startswith("PGV-SEED-")
    # Same vector → similarity near 1.0
    assert float(top["similarity"]) > 0.99
