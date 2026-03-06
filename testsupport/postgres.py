from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncConnection

DEFAULT_DATABASE_URL = "postgresql+asyncpg://twype:twype_secret@localhost:5433/twype"
TEST_DATABASE_SUFFIX = "_test"

_ensured_databases: set[str] = set()


def default_test_database_url(env: Mapping[str, str] | None = None) -> str:
    values = {**_root_env_values(), **(env if env is not None else os.environ)}
    explicit_test_url = values.get("TEST_DATABASE_URL")
    if explicit_test_url:
        return _normalize_host_database_url(explicit_test_url)

    base_url = values.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    parsed_url = make_url(_normalize_host_database_url(base_url))
    database_name = parsed_url.database or "postgres"

    if database_name.endswith(TEST_DATABASE_SUFFIX):
        return _render_database_url(parsed_url)

    return _render_database_url(parsed_url.set(database=f"{database_name}{TEST_DATABASE_SUFFIX}"))


async def ensure_database_exists(database_url: str) -> None:
    if database_url in _ensured_databases:
        return

    target_url = make_url(database_url)
    target_database = target_url.database
    if not target_database:
        raise RuntimeError("Test database URL must include a database name")

    quoted_database = target_database.replace('"', '""')
    for admin_url in _admin_database_urls(target_url):
        try:
            connection = await asyncpg.connect(
                user=admin_url.username,
                password=admin_url.password,
                host=admin_url.host,
                port=admin_url.port,
                database=admin_url.database,
                ssl=_asyncpg_ssl_setting(admin_url),
            )
        except asyncpg.InvalidCatalogNameError:
            continue

        try:
            exists = await connection.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                target_database,
            )
            if not exists:
                await connection.execute(f'CREATE DATABASE "{quoted_database}"')
            _ensured_databases.add(database_url)
            return
        finally:
            await connection.close()

    raise RuntimeError(f"Unable to connect to an admin database for {target_database}")


def _admin_database_urls(database_url: URL) -> list[URL]:
    candidates: list[str] = []
    target_database = database_url.database or "postgres"
    if target_database.endswith(TEST_DATABASE_SUFFIX):
        base_database = target_database[: -len(TEST_DATABASE_SUFFIX)]
        if base_database:
            candidates.append(base_database)
    if target_database != "postgres":
        candidates.append("postgres")
    if target_database not in candidates:
        candidates.append(target_database)

    unique_candidates: list[URL] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(database_url.set(database=candidate))
    return unique_candidates


def _normalize_host_database_url(database_url: str) -> str:
    parsed_url = make_url(database_url)
    if parsed_url.host != "postgres" or _running_in_docker():
        return _render_database_url(parsed_url)

    port = parsed_url.port
    if port in (None, 5432):
        port = 5433
    return _render_database_url(parsed_url.set(host="localhost", port=port))


@lru_cache(maxsize=1)
def _root_env_values() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


@lru_cache(maxsize=1)
def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _asyncpg_ssl_setting(database_url: URL) -> bool | None:
    sslmode = database_url.query.get("sslmode") if database_url.query else None
    if sslmode == "disable":
        return False
    if sslmode in {"require", "verify-ca", "verify-full"}:
        return True
    if database_url.host in {"localhost", "127.0.0.1", "postgres"}:
        return False
    return None


def _render_database_url(database_url: URL) -> str:
    return database_url.render_as_string(hide_password=False)


async def ensure_pgvector_extension(connection: AsyncConnection) -> None:
    await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
