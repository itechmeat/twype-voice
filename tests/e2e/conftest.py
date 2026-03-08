from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy.engine import make_url

from .helpers import AuthContext

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_API_BASE_URL = "http://localhost/api"
DEFAULT_LIVEKIT_URL = "ws://localhost/livekit-signaling"
DEFAULT_DATABASE_URL = "postgresql+asyncpg://twype:twype_secret@localhost:5433/twype"
REQUIRED_COMPOSE_SERVICES = ("postgres", "livekit", "litellm", "caddy", "api", "agent", "web")


@dataclass(slots=True, frozen=True)
class E2ESettings:
    api_base_url: str
    livekit_url: str
    database_url: str


def _load_root_env() -> dict[str, str]:
    env_path = ROOT_DIR / ".env"
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


def _normalize_database_url(database_url: str) -> str:
    parsed = make_url(database_url)
    normalized = parsed

    if parsed.drivername.endswith("+asyncpg"):
        normalized = normalized.set(drivername="postgresql")

    if parsed.host == "postgres":
        normalized = normalized.set(host="localhost", port=5433)

    return normalized.render_as_string(hide_password=False)


def _parse_compose_ps_output(raw_output: str) -> dict[str, dict[str, object]]:
    raw_output = raw_output.strip()
    if not raw_output:
        return {}

    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, list):
            return {
                str(item.get("Service") or item.get("Name")): item
                for item in parsed
                if isinstance(item, dict)
            }
    except json.JSONDecodeError:
        pass

    services: dict[str, dict[str, object]] = {}
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed_line = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed_line, dict):
            continue
        key = str(parsed_line.get("Service") or parsed_line.get("Name"))
        services[key] = parsed_line
    return services


def _service_is_healthy(service: dict[str, object]) -> bool:
    state = str(service.get("State", "")).lower()
    health = str(service.get("Health", "")).lower()

    if health:
        return health == "healthy"

    if "healthy" in state:
        return True

    return state == "running"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    markexpr = (config.option.markexpr or "").strip()
    if markexpr and "external" in markexpr:
        return

    skip_external = pytest.mark.skip(reason="requires `pytest tests/e2e/ -m external`")
    for item in items:
        if "external" in item.keywords:
            item.add_marker(skip_external)


@pytest.fixture(scope="session")
def e2e_settings() -> E2ESettings:
    env_values = {
        **_load_root_env(),
        **os.environ,
    }
    return E2ESettings(
        api_base_url=env_values.get("E2E_API_BASE_URL", DEFAULT_API_BASE_URL),
        livekit_url=env_values.get("E2E_LIVEKIT_URL", DEFAULT_LIVEKIT_URL),
        database_url=_normalize_database_url(env_values.get("DATABASE_URL", DEFAULT_DATABASE_URL)),
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_compose_services_healthy() -> None:
    docker_executable = shutil.which("docker")
    if docker_executable is None:
        raise pytest.UsageError("docker is required for tests/e2e")

    try:
        result = subprocess.run(  # noqa: S603
            [docker_executable, "compose", "ps", "--format", "json"],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise pytest.UsageError(
            f"docker compose ps failed with exit code {exc.returncode}: {exc.stderr.strip()}"
        ) from exc

    services = _parse_compose_ps_output(result.stdout)
    missing_services = [
        service_name for service_name in REQUIRED_COMPOSE_SERVICES if service_name not in services
    ]
    if missing_services:
        raise pytest.UsageError(
            "Docker Compose stack is incomplete. Missing services: "
            + ", ".join(sorted(missing_services))
        )

    unhealthy_services = [
        service_name
        for service_name in REQUIRED_COMPOSE_SERVICES
        if not _service_is_healthy(services[service_name])
    ]
    if unhealthy_services:
        raise pytest.UsageError(
            "Docker Compose services are not healthy: " + ", ".join(sorted(unhealthy_services))
        )


@pytest.fixture
async def api_client(e2e_settings: E2ESettings) -> AsyncClient:
    async with AsyncClient(base_url=e2e_settings.api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
async def db_connection(e2e_settings: E2ESettings):
    connection = await asyncpg.connect(e2e_settings.database_url)
    try:
        yield connection
    finally:
        await connection.close()


@pytest.fixture
def unique_email() -> str:
    return f"e2e-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
async def registered_user(api_client: AsyncClient, unique_email: str) -> tuple[str, str]:
    password = "strongpass123"
    response = await api_client.post(
        "/auth/register",
        json={"email": unique_email, "password": password},
        headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    response.raise_for_status()
    return unique_email, password


@pytest.fixture
async def verified_user(
    api_client: AsyncClient,
    db_connection: asyncpg.Connection,
    registered_user: tuple[str, str],
) -> AuthContext:
    email, password = registered_user
    verification_code = await db_connection.fetchval(
        "SELECT verification_code FROM users WHERE email = $1",
        email,
    )
    if not verification_code:
        raise RuntimeError(f"verification code was not generated for {email}")

    verify_response = await api_client.post(
        "/auth/verify",
        json={"email": email, "code": verification_code},
        headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    verify_response.raise_for_status()
    verify_payload = verify_response.json()

    return AuthContext(
        email=email,
        password=password,
        access_token=str(verify_payload["access_token"]),
        refresh_token=str(verify_payload["refresh_token"]),
    )


@pytest.fixture
async def authenticated_client(
    api_client: AsyncClient,
    verified_user: AuthContext,
) -> AsyncClient:
    api_client.headers.update({"Authorization": f"Bearer {verified_user.access_token}"})
    return api_client
