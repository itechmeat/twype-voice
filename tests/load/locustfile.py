from __future__ import annotations

from locust import between, events, task

from tests.load.livekit_user import LiveKitUser, SessionStartPayload


@events.init_command_line_parser.add_listener
def add_locust_arguments(parser) -> None:
    parser.add_argument(
        "--livekit-url",
        default="ws://localhost/livekit-signaling",
        help="LiveKit signaling URL exposed by the local Docker Compose stack.",
    )


class TwypeLoadUser(LiveKitUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.email = self.build_unique_email()
        self.password = "strongpass123"
        self.livekit_url = (
            self.environment.parsed_options.livekit_url or "ws://localhost/livekit-signaling"
        )

        register_response = self.client.post(
            "/auth/register",
            json={"email": self.email, "password": self.password},
            name="/auth/register",
        )
        register_response.raise_for_status()

        verification_code = self.run_async(self.fetch_verification_code(self.email))

        verify_response = self.client.post(
            "/auth/verify",
            json={"email": self.email, "code": verification_code},
            name="/auth/verify",
        )
        verify_response.raise_for_status()
        verify_payload = verify_response.json()

        self.client.headers.update({"Authorization": f"Bearer {verify_payload['access_token']}"})

    @task
    def auth_session_text_cycle(self) -> None:
        session_response = self.client.post("/sessions/start", name="/sessions/start")
        session_response.raise_for_status()
        session_payload = SessionStartPayload(**session_response.json())

        self.run_async(
            self.join_room(
                livekit_url=self.livekit_url,
                token=session_payload.livekit_token,
            )
        )

        try:
            self.run_async(self.send_text_message("Share one grounding tip for acute stress."))

            history_response = self.client.get(
                "/sessions/history?limit=5", name="/sessions/history"
            )
            history_response.raise_for_status()
        finally:
            self.run_async(self.leave_room())
