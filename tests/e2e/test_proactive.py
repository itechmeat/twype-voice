from __future__ import annotations

import pytest

from .helpers import started_livekit_session


@pytest.mark.external
async def test_proactive_nudge_after_silence(
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

        proactive_message = await started_session.room.wait_for_message(
            wait_seconds=25.0,
            allowed_types={"proactive_nudge"},
        )

    assert proactive_message.payload["type"] == "proactive_nudge"
    assert proactive_message.payload["proactive_type"] in {"follow_up", "extended_silence"}
