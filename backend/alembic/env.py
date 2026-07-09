"""Alembic environment placeholder.

The project currently ships historical SQL migrations under backend/migrations
and applies them through apply_migrations.py for deterministic upgrades. Alembic
is included so future model-driven revisions can be introduced without changing
repository layout.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_url() -> str:
    url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def run_migrations_offline() -> None:
    context.configure(url=_sync_url(), target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
