from __future__ import annotations

from httpx import AsyncClient


async def test_auth_flow(
    api_client: AsyncClient,
    db_connection,
    unique_email: str,
) -> None:
    password = "strongpass123"

    register_response = await api_client.post(
        "/auth/register",
        json={"email": unique_email, "password": password},
        headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    assert register_response.status_code == 201

    verification_code = await db_connection.fetchval(
        "SELECT verification_code FROM users WHERE email = $1",
        unique_email,
    )
    assert verification_code

    verify_response = await api_client.post(
        "/auth/verify",
        json={"email": unique_email, "code": verification_code},
    )
    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["access_token"]
    assert verify_payload["refresh_token"]

    login_response = await api_client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["access_token"]
    assert login_payload["refresh_token"]

    refresh_response = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["access_token"]
    assert refresh_payload["refresh_token"]
