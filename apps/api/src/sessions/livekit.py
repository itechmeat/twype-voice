from __future__ import annotations

from datetime import timedelta

from livekit import api

_TOKEN_TTL = timedelta(hours=6)


def create_livekit_token(identity: str, room_name: str, api_key: str, api_secret: str) -> str:
    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_grants(grants)
        .with_ttl(_TOKEN_TTL)
    )
    return token.to_jwt()
