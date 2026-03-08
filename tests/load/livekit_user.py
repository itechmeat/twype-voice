from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import asyncpg
from livekit import rtc
from locust import HttpUser, events
from sqlalchemy.engine import make_url

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql+asyncpg://twype:twype_secret@localhost:5433/twype"


@dataclass(slots=True, frozen=True)
class SessionStartPayload:
    session_id: str
    room_name: str
    livekit_token: str


class LiveKitUser(HttpUser):
    abstract = True

    def __init__(self, environment) -> None:
        super().__init__(environment)
        self._room: rtc.Room | None = None
        self._room_messages: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._database_url = self._resolve_database_url()
        # Persistent event loop so rtc.Room internal coroutines survive across calls.
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever, daemon=True
        )
        self._loop_thread.start()

    def _record_request(
        self,
        *,
        name: str,
        started_at: float,
        exception: Exception | None = None,
    ) -> None:
        events.request.fire(
            request_type="livekit",
            name=name,
            response_time=(time.perf_counter() - started_at) * 1000,
            response_length=0,
            response=None,
            context={},
            exception=exception,
        )

    async def join_room(self, *, livekit_url: str, token: str) -> None:
        started_at = time.perf_counter()
        room = rtc.Room()

        @room.on("data_received")
        def _on_data_received(data_packet: rtc.DataPacket) -> None:
            try:
                payload = json.loads(data_packet.data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return
            if isinstance(payload, dict):
                self._room_messages.put_nowait(payload)

        try:
            await room.connect(livekit_url, token, rtc.RoomOptions(auto_subscribe=True))
        except Exception as exc:  # pragma: no cover - load runtime path
            self._record_request(name="room_connect", started_at=started_at, exception=exc)
            raise

        self._room = room
        self._record_request(name="room_connect", started_at=started_at)

    async def leave_room(self) -> None:
        if self._room is None:
            return

        await self._room.disconnect()
        self._room = None

    async def send_text_message(
        self,
        text: str,
        *,
        wait_seconds: float = 30.0,
    ) -> dict[str, object]:
        if self._room is None:
            raise RuntimeError("room is not connected")

        started_at = time.perf_counter()
        await self._room.local_participant.publish_data(
            json.dumps({"type": "chat_message", "text": text}, separators=(",", ":")),
            reliable=True,
        )

        while True:
            remaining = wait_seconds - (time.perf_counter() - started_at)
            if remaining <= 0:
                raise TimeoutError("timed out waiting for structured_response")
            payload = await asyncio.wait_for(
                self._room_messages.get(), timeout=remaining
            )
            if payload.get("type") != "structured_response":
                continue
            self._record_request(name="text_round_trip", started_at=started_at)
            return payload

    def run_async(self, coroutine):
        """Run a coroutine on the persistent event loop from a sync context."""
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        return future.result(timeout=60)

    def cleanup_loop(self) -> None:
        """Stop the background event loop and join its thread."""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop_thread.join(timeout=5)
        self._loop.close()

    def build_unique_email(self) -> str:
        return f"load-{uuid.uuid4().hex[:10]}@example.com"

    async def fetch_verification_code(self, email: str) -> str:
        connection = await asyncpg.connect(self._database_url)
        try:
            verification_code = await connection.fetchval(
                "SELECT verification_code FROM users WHERE email = $1",
                email,
            )
        finally:
            await connection.close()

        if not verification_code:
            raise RuntimeError(f"verification code is missing for {email}")

        return str(verification_code)

    def _resolve_database_url(self) -> str:
        env_values = {
            **self._load_root_env(),
            **os.environ,
        }
        return self._normalize_database_url(env_values.get("DATABASE_URL", DEFAULT_DATABASE_URL))

    def _load_root_env(self) -> dict[str, str]:
        env_path = ROOT_DIR / ".env"
        if not env_path.exists():
            return {}

        values: dict[str, str] = {}
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
        return values

    def _normalize_database_url(self, database_url: str) -> str:
        parsed = make_url(database_url)
        normalized = parsed

        if parsed.drivername.endswith("+asyncpg"):
            normalized = normalized.set(drivername="postgresql")

        if parsed.host == "postgres":
            normalized = normalized.set(host="localhost", port=5433)

        return normalized.render_as_string(hide_password=False)
