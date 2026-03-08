from __future__ import annotations

import pytest

from .helpers import contains_cyrillic, contains_latin, started_livekit_session


@pytest.mark.external
@pytest.mark.parametrize(
    ("message_text", "detector"),
    [
        ("Explain one practical way to calm acute stress.", contains_latin),
        (
            "\u041f\u043e\u0434\u0441\u043a\u0430\u0436\u0438 \u043e\u0434\u0438\u043d "
            "\u043f\u0440\u0430\u043a\u0442\u0438\u0447\u043d\u044b\u0439 "
            "\u0441\u043f\u043e\u0441\u043e\u0431 \u0441\u043d\u0438\u0437\u0438\u0442\u044c "
            "\u043e\u0441\u0442\u0440\u044b\u0439 \u0441\u0442\u0440\u0435\u0441\u0441.",
            contains_cyrillic,
        ),
    ],
)
async def test_bilingual_text_responses(
    authenticated_client,
    e2e_settings,
    verified_user,
    message_text: str,
    detector,
) -> None:
    async with started_livekit_session(
        client=authenticated_client,
        access_token=verified_user.access_token,
        livekit_url=e2e_settings.livekit_url,
    ) as started_session:
        await started_session.room.wait_for_remote_participant(wait_seconds=15.0)
        await started_session.room.send_chat_message(message_text)

        structured_message = await started_session.room.wait_for_message(
            wait_seconds=30.0,
            allowed_types={"structured_response"},
            predicate=lambda message: bool(message.payload.get("is_final")),
        )

    response_text = " ".join(
        item.get("text", "")
        for item in structured_message.payload.get("items", [])
        if isinstance(item, dict)
    )
    assert response_text
    assert detector(response_text)
