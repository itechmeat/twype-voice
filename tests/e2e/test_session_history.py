from __future__ import annotations

import pytest

from .helpers import auth_headers, started_livekit_session


@pytest.mark.external
async def test_session_history_and_messages(
    authenticated_client,
    e2e_settings,
    verified_user,
) -> None:
    async with started_livekit_session(
        client=authenticated_client,
        access_token=verified_user.access_token,
        livekit_url=e2e_settings.livekit_url,
    ) as started_session:
        await started_session.room.wait_for_remote_participant(wait_seconds=15.0)
        await started_session.room.send_chat_message("Give me one grounding step.")
        await started_session.room.wait_for_message(
            wait_seconds=30.0,
            allowed_types={"structured_response"},
            predicate=lambda message: bool(message.payload.get("is_final")),
        )

    history_response = await authenticated_client.get(
        "/sessions/history",
        headers=auth_headers(verified_user.access_token),
    )
    assert history_response.status_code == 200
    history_items = history_response.json()["items"]
    assert any(item["id"] == started_session.session_id for item in history_items)

    messages_response = await authenticated_client.get(
        f"/sessions/{started_session.session_id}/messages",
        headers=auth_headers(verified_user.access_token),
    )
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) >= 2
