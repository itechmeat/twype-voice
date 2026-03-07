from __future__ import annotations

import asyncio
import os

import resend

from src.localization import translate

VERIFICATION_CODE_TTL_MINUTES = 10


async def send_verification_code(
    email: str,
    code: str,
    *,
    locale: str | None = None,
) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    from_address = os.environ.get("EMAIL_FROM", "Twype <noreply@twype.app>")

    resend.api_key = api_key
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": from_address,
            "to": [email],
            "subject": translate("auth.email_verification_subject", locale=locale),
            "html": translate(
                "auth.email_verification_html",
                locale=locale,
                params={
                    "code": code,
                    "ttl_minutes": VERIFICATION_CODE_TTL_MINUTES,
                },
            ),
        },
    )
