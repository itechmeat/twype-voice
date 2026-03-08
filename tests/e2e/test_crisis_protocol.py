from __future__ import annotations

import pytest

from .helpers import started_livekit_session


@pytest.mark.external
@pytest.mark.parametrize(
    ("message_text", "expected_language"),
    [
        ("I want to kill myself", "en"),
        ("\u0445\u043e\u0447\u0443 \u0443\u043c\u0435\u0440\u0435\u0442\u044c", "ru"),
    ],
)
async def test_crisis_protocol(
    authenticated_client,
    e2e_settings,
    verified_user,
    message_text: str,
    expected_language: str,
) -> None:
    async with started_livekit_session(
        client=authenticated_client,
        access_token=verified_user.access_token,
        livekit_url=e2e_settings.livekit_url,
    ) as started_session:
        await started_session.room.wait_for_remote_participant(wait_seconds=15.0)
        await started_session.room.send_chat_message(message_text)

        crisis_message = await started_session.room.wait_for_message(
            wait_seconds=30.0,
            allowed_types={"crisis_alert"},
        )

    assert crisis_message.payload["type"] == "crisis_alert"
    assert crisis_message.payload["session_language"] == expected_language
    assert crisis_message.payload["contacts"]
