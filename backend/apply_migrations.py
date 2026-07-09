"""Apply SQL migrations at container startup.

PostgreSQL's /docker-entrypoint-initdb.d only runs on an empty data directory.
For SaaS upgrades we must apply migrations on every deploy. This lightweight
runner keeps the current SQL-migration layout reliable until the project fully
moves to autogenerating Alembic revisions.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())")
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        if not migrations_dir.exists():
            print("No migrations directory found; skipping")
            return
        for path in sorted(migrations_dir.glob("*.sql")):
            version = path.name
            already = await conn.fetchval("SELECT 1 FROM schema_migrations WHERE version=$1", version)
            if already:
                continue
            print(f"Applying migration {version}")
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute("INSERT INTO schema_migrations(version) VALUES($1)", version)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
