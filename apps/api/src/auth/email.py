from __future__ import annotations

import asyncio
import os

import resend


async def send_verification_code(email: str, code: str) -> None:
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
            "subject": "Twype — код подтверждения",
            "html": (
                f"<p>Ваш код подтверждения: <strong>{code}</strong></p>"
                "<p>Код действителен 10 минут.</p>"
            ),
        },
    )
