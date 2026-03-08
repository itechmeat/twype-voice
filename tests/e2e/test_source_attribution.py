from __future__ import annotations

import pytest

from .helpers import auth_headers, extract_chunk_ids, started_livekit_session


@pytest.mark.external
async def test_source_attribution_flow(
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
            "Which grounding method helps bring attention back to the present moment?"
        )

        structured_message = await started_session.room.wait_for_message(
            wait_seconds=30.0,
            allowed_types={"structured_response"},
            predicate=lambda message: bool(message.payload.get("is_final")),
        )

    chunk_ids = extract_chunk_ids(structured_message.payload)
    assert chunk_ids

    resolve_response = await authenticated_client.post(
        "/sources/resolve",
        headers=auth_headers(verified_user.access_token),
        json={"chunk_ids": chunk_ids},
    )
    assert resolve_response.status_code == 200
    resolved_items = resolve_response.json()["items"]
    assert resolved_items
    assert all(item["source_type"] for item in resolved_items)
    assert all(item["title"] for item in resolved_items)
