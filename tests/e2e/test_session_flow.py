from __future__ import annotations

from .helpers import started_livekit_session


async def test_start_session_and_agent_joins(
    authenticated_client,
    e2e_settings,
    verified_user,
) -> None:
    async with started_livekit_session(
        client=authenticated_client,
        access_token=verified_user.access_token,
        livekit_url=e2e_settings.livekit_url,
    ) as started_session:
        participant = await started_session.room.wait_for_remote_participant(wait_seconds=15.0)

    assert started_session.session_id
    assert started_session.room_name.startswith("session-")
    assert participant.identity
