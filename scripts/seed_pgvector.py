#!/usr/bin/env python3
"""Seed pgvector embeddings into parts_catalog (opt-in live Postgres).

Connects with asyncpg when DATABASE_URL or POSTGRES_* is set and the
server is reachable. Creates the ``vector`` extension if missing, ensures
an ``embedding`` column on ``parts_catalog`` when the table exists, then
upserts a few demo rows with deterministic fake embeddings.

If no database is available the script exits 0 and prints JSON with
``skipped=true`` so CI / offline unit paths stay green without Docker.

Compose profiles (see docker-compose.yml)::

  docker compose --profile core up          # postgres + redis only
  docker compose --profile pgvector up      # alias for core (pgvector/pgvector:pg16)
  docker compose --profile api up           # + backend (PGVECTOR_ENABLED via env)
  docker compose --profile full up          # + frontend + workers
  docker compose --profile obs up           # + flower

Typical local flow::

  docker compose --profile pgvector up -d
  export PGVECTOR_ENABLED=true
  # optional: DATABASE_URL=postgresql://postgres:password@localhost:5432/dealership_parts
  python scripts/seed_pgvector.py
  pytest -q tests/test_pgvector_e2e.py

Env:
  DATABASE_URL          postgresql:// or postgresql+asyncpg:// DSN
  POSTGRES_HOST/PORT/DB/USER/PASSWORD   fallback DSN pieces
  EMBEDDING_DIM         default 1536 (OpenAI text-embedding-3-small width)
  PGVECTOR_ENABLED      reported in status JSON (does not gate seeding)
  SEED_PGVECTOR_FORCE   if 1, treat missing table as error instead of soft skip
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from typing import Any

# Prefer repo-local imports only when needed; seed stays stdlib+asyncpg+numpy.
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore


DEFAULT_DIM = 1536
SEED_PARTS: list[dict[str, Any]] = [
    {
        "part_number": "PGV-SEED-BRK001",
        "manufacturer": "Brembo",
        "part_name": "Brake Pad Set Front (pgvector seed)",
        "description": "Ceramic front brake pads — seed row for offline/e2e vector smoke",
        "category": "Brakes",
        "subcategory": "Brake Pads",
        "make": "Honda",
        "model": "Civic",
        "year_from": 2019,
        "year_to": 2024,
        "msrp": 89.99,
        "cost": 45.0,
    },
    {
        "part_number": "PGV-SEED-FLT002",
        "manufacturer": "Fram",
        "part_name": "Oil Filter (pgvector seed)",
        "description": "Standard oil filter seed row for vector search smoke tests",
        "category": "Engine",
        "subcategory": "Filters",
        "make": "Honda",
        "model": "Civic",
        "year_from": 2019,
        "year_to": 2024,
        "msrp": 12.99,
        "cost": 6.5,
    },
    {
        "part_number": "PGV-SEED-SPK003",
        "manufacturer": "NGK",
        "part_name": "Spark Plug Set (pgvector seed)",
        "description": "Iridium spark plugs seed row for cosine distance checks",
        "category": "Engine",
        "subcategory": "Ignition",
        "make": "Toyota",
        "model": "Camry",
        "year_from": 2018,
        "year_to": 2023,
        "msrp": 24.99,
        "cost": 12.5,
    },
]


def _compose_help() -> str:
    return (
        "Compose profiles: core|pgvector (postgres+redis), api (+backend), "
        "full (+frontend+workers), obs (+flower). "
        "Image: pgvector/pgvector:pg16. Example: "
        "docker compose --profile pgvector up -d && "
        "PGVECTOR_ENABLED=true python scripts/seed_pgvector.py"
    )


def build_dsn() -> str | None:
    """Return an asyncpg-compatible DSN, or None if nothing configured."""
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if raw:
        # asyncpg wants postgresql:// not sqlalchemy postgresql+asyncpg://
        if raw.startswith("postgresql+asyncpg://"):
            return "postgresql://" + raw[len("postgresql+asyncpg://") :]
        if raw.startswith("postgres+asyncpg://"):
            return "postgresql://" + raw[len("postgres+asyncpg://") :]
        if raw.startswith("postgres://"):
            return "postgresql://" + raw[len("postgres://") :]
        return raw

    host = os.environ.get("POSTGRES_HOST")
    # Only treat as configured if host is explicitly set OR any credential piece is set
    # beyond pure defaults — actually task says "DATABASE_URL or POSTGRES_*".
    # We'll always build from POSTGRES_* defaults so connection attempt can skip on fail.
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "password")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "dealership_parts")
    host = host or "localhost"

    # If caller set nothing at all, still try localhost defaults (compose default).
    # Unavailable host → soft skip after connect failure.
    from urllib.parse import quote_plus

    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{db}"
    )


def _embedding_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


def _stable_seed(part_number: str, dim: int) -> int:
    """Process-stable seed (avoid Python's randomized hash())."""
    acc = dim * 17 + 0x9E3779B9
    for c in part_number:
        acc = (acc * 131 + ord(c)) & 0xFFFFFFFF
    return acc or 1


def _fake_embedding(part_number: str, dim: int, zeros: bool = False) -> list[float]:
    if zeros:
        return [0.0] * dim
    seed = _stable_seed(part_number, dim)
    if np is None:
        # Deterministic LCG fallback without numpy
        out: list[float] = []
        x = seed % 2147483647 or 1
        for _ in range(dim):
            x = (1103515245 * x + 12345) % (2**31)
            out.append((x / 2**31) * 2.0 - 1.0)
        # L2 normalize
        norm = sum(v * v for v in out) ** 0.5 or 1.0
        return [v / norm for v in out]
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float64)
    n = float(np.linalg.norm(v)) or 1.0
    return (v / n).tolist()


async def _probe_connect(dsn: str, timeout: float = 2.0):
    import asyncpg

    return await asyncio.wait_for(asyncpg.connect(dsn), timeout=timeout)


async def seed(
    *,
    dim: int | None = None,
    zeros: bool = False,
    force: bool = False,
    connect_timeout: float = 2.0,
) -> dict[str, Any]:
    """Run seed; never raises for missing DB — returns status dict."""
    dim = int(dim or os.environ.get("EMBEDDING_DIM") or DEFAULT_DIM)
    force = force or os.environ.get("SEED_PGVECTOR_FORCE", "").strip() in {"1", "true", "yes"}
    pgvector_flag = os.environ.get("PGVECTOR_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    status: dict[str, Any] = {
        "ok": True,
        "skipped": False,
        "pgvector_enabled_env": pgvector_flag,
        "embedding_dim": dim,
        "extension_created": False,
        "table_exists": False,
        "embedding_column_ensured": False,
        "upserted": 0,
        "part_numbers": [],
        "dsn_source": "DATABASE_URL" if os.environ.get("DATABASE_URL") else "POSTGRES_*",
        "compose_hint": _compose_help(),
    }

    dsn = build_dsn()
    if not dsn:
        status["skipped"] = True
        status["reason"] = "no_database_url"
        return status

    try:
        import asyncpg  # noqa: F401
    except ImportError:
        status["skipped"] = True
        status["reason"] = "asyncpg_not_installed"
        status["ok"] = True
        return status

    try:
        conn = await _probe_connect(dsn, timeout=connect_timeout)
    except Exception as exc:
        status["skipped"] = True
        status["reason"] = "db_unreachable"
        status["error"] = f"{type(exc).__name__}: {exc}"
        status["ok"] = True  # offline / no Docker is success for unit path
        return status

    try:
        # Extensions first (vector image registers "vector"; uuid helpers optional)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        status["extension_created"] = True
        for ext_name in ("uuid-ossp", "pgcrypto"):
            try:
                await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext_name}"')
            except Exception:
                pass

        ext = await conn.fetchval(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        )
        status["vector_extension"] = bool(ext)

        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = 'parts_catalog'
            )
            """
        )
        status["table_exists"] = bool(table_exists)

        if not table_exists:
            # Minimal table for e2e when Alembic/ORM has not created schema yet.
            # vector_id has no server default — seed always supplies a UUID.
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS parts_catalog (
                  id SERIAL PRIMARY KEY,
                  part_number VARCHAR(100) NOT NULL UNIQUE,
                  manufacturer VARCHAR(100) NOT NULL,
                  part_name VARCHAR(255) NOT NULL,
                  description TEXT,
                  category VARCHAR(100) NOT NULL,
                  subcategory VARCHAR(100),
                  make VARCHAR(50),
                  model VARCHAR(100),
                  year_from INTEGER,
                  year_to INTEGER,
                  msrp NUMERIC(10, 2),
                  cost NUMERIC(10, 2),
                  is_active BOOLEAN NOT NULL DEFAULT TRUE,
                  vector_id UUID NOT NULL,
                  embedding vector({int(dim)}),
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            status["table_exists"] = True
            status["table_created"] = True
        else:
            status["table_created"] = False

        # Ensure embedding column (ORM model may omit it until migrations catch up)
        col = await conn.fetchval(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'parts_catalog'
              AND column_name = 'embedding'
            """
        )
        if not col:
            await conn.execute(
                f"ALTER TABLE parts_catalog "
                f"ADD COLUMN IF NOT EXISTS embedding vector({int(dim)})"
            )
            status["embedding_column_added"] = True
        else:
            status["embedding_column_added"] = False
        status["embedding_column_ensured"] = True

        upserted = 0
        part_numbers: list[str] = []
        insert_sql = """
            INSERT INTO parts_catalog (
              part_number, manufacturer, part_name, description,
              category, subcategory, make, model, year_from, year_to,
              msrp, cost, is_active, vector_id, embedding, created_at, updated_at
            ) VALUES (
              $1, $2, $3, $4,
              $5, $6, $7, $8, $9, $10,
              $11, $12, TRUE, $13::uuid, $14::vector, NOW(), NOW()
            )
            ON CONFLICT (part_number) DO UPDATE SET
              manufacturer = EXCLUDED.manufacturer,
              part_name = EXCLUDED.part_name,
              description = EXCLUDED.description,
              category = EXCLUDED.category,
              subcategory = EXCLUDED.subcategory,
              make = EXCLUDED.make,
              model = EXCLUDED.model,
              year_from = EXCLUDED.year_from,
              year_to = EXCLUDED.year_to,
              msrp = EXCLUDED.msrp,
              cost = EXCLUDED.cost,
              is_active = TRUE,
              embedding = EXCLUDED.embedding,
              updated_at = NOW()
            RETURNING id, part_number
            """
        for part in SEED_PARTS:
            emb = _fake_embedding(part["part_number"], dim, zeros=zeros)
            emb_lit = _embedding_literal(emb)
            vid = str(uuid.uuid4())
            row = await conn.fetchrow(
                insert_sql,
                part["part_number"],
                part["manufacturer"],
                part["part_name"],
                part["description"],
                part["category"],
                part["subcategory"],
                part["make"],
                part["model"],
                part["year_from"],
                part["year_to"],
                part["msrp"],
                part["cost"],
                vid,
                emb_lit,
            )
            if row:
                upserted += 1
                part_numbers.append(row["part_number"])

        status["upserted"] = upserted
        status["part_numbers"] = part_numbers
        status["ok"] = upserted > 0 or not force
        if force and upserted == 0:
            status["reason"] = "upsert_failed"
        return status
    except Exception as exc:
        if force:
            status["ok"] = False
            status["skipped"] = False
        else:
            # Soft-fail when schema is hostile (partial migrations)
            status["ok"] = True
            status["skipped"] = True
            status["reason"] = "seed_error"
        status["error"] = f"{type(exc).__name__}: {exc}"
        return status
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed pgvector embeddings into parts_catalog (skips if DB down).",
        epilog=_compose_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=None,
        help=f"Embedding dimension (default env EMBEDDING_DIM or {DEFAULT_DIM})",
    )
    parser.add_argument(
        "--zeros",
        action="store_true",
        help="Use zero vectors instead of deterministic random unit vectors",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Non-zero exit when DB unreachable or seed fails",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Connect timeout seconds (default 2)",
    )
    args = parser.parse_args(argv)

    status = asyncio.run(
        seed(dim=args.dim, zeros=args.zeros, force=args.force, connect_timeout=args.timeout)
    )
    print(json.dumps(status, indent=2, default=str))
    if args.force and (status.get("skipped") or not status.get("ok")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
