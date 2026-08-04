"""Alembic env for Parts DMS Postgres schema."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# monorepo src on path
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from parrts.dms.backend import build_postgres_url_from_env  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # pure SQL migrations


def get_url() -> str:
    url = build_postgres_url_from_env()
    if not url:
        raise RuntimeError(
            "Alembic needs DMS_DATABASE_URL, DATABASE_URL, or POSTGRES_HOST "
            "(+ POSTGRES_DB/USER/PASSWORD)"
        )
    # SQLAlchemy 2 prefers postgresql+psycopg2
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        connection.execute(text("SELECT 1"))


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
