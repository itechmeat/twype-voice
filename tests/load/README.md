# Load Testing

These load tests target the full local Docker Compose stack and simulate the MVP text-chat flow:
registration, verification, authenticated session start, LiveKit room join, text message round-trip,
and session history fetch.

## Prerequisites

- `docker compose up` is running and all services are healthy
- Root `.env` contains valid provider credentials for the stack you want to exercise
- `locust` is installed through the root Python workspace

## Commands

Run with the Locust web UI:

```bash
uv run locust -f tests/load/locustfile.py --host http://localhost/api
```

Run headless for the baseline scenario:

```bash
uv run locust -f tests/load/locustfile.py \
  --host http://localhost/api \
  --users 30 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless
```

Override the LiveKit signaling URL when needed:

```bash
uv run locust -f tests/load/locustfile.py \
  --host http://localhost/api \
  --livekit-url ws://localhost/livekit-signaling
```

## Notes

- The current scenario is text-first to avoid STT/TTS rate limits during the baseline run.
- `tests/load/livekit_user.py` records custom `livekit` request metrics for room join latency and
  text round-trip latency.
- The verification code is fetched directly from the local PostgreSQL database, so the load runner
  must be able to reach the Compose Postgres instance on `localhost:5433` (or via the normalized
  `DATABASE_URL` from the root `.env`).

## Performance Targets

- 30 concurrent users for 5 minutes
- Aggregate error rate below 5%
- p95 API latency below 500 ms for auth and session endpoints
- Stable LiveKit room join times and text round-trip latency throughout the run
