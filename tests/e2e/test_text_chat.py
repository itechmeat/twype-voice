from __future__ import annotations

import pytest

from .helpers import started_livekit_session


@pytest.mark.external
async def test_text_chat_round_trip(
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
        await started_session.room.send_chat_message(
            "What is one grounding technique that helps during acute stress?"
        )

        response_message = await started_session.room.wait_for_message(
            wait_seconds=30.0,
            allowed_types={"structured_response"},
            predicate=lambda message: bool(message.payload.get("is_final")),
        )

    assert response_message.payload["type"] == "structured_response"
    assert response_message.payload["items"]
