## ADDED Requirements

### Requirement: Start session and obtain LiveKit token
The system SHALL call `POST /sessions/start` via `apiFetch` when the chat page mounts. The response SHALL contain `session_id` (string), `room_name` (string), and `livekit_token` (string). The system SHALL store `session_id` in component state for use by child components.

#### Scenario: Successful session start
- **WHEN** the chat page mounts and the user is authenticated
- **THEN** the system SHALL call `POST /sessions/start` and receive `session_id`, `room_name`, and `livekit_token`

#### Scenario: Session start failure
- **WHEN** `POST /sessions/start` returns an error
- **THEN** the system SHALL display an error message and provide a retry option

#### Scenario: Token refresh during session start
- **WHEN** `POST /sessions/start` returns 401
- **THEN** `apiFetch` SHALL automatically refresh the JWT and retry the request

### Requirement: Connect to LiveKit room with token
The system SHALL render a `LiveKitRoom` component configured with the `livekit_token` and the LiveKit signaling URL. The signaling URL SHALL be constructed as `wss://<current_host>/livekit-signaling/` in production or `ws://localhost/livekit-signaling/` in development (matching the Caddy proxy path). The `LiveKitRoom` SHALL enable `autoSubscribe` for audio tracks.

#### Scenario: Room connection established
- **WHEN** the `LiveKitRoom` component receives a valid token and URL
- **THEN** the client SHALL establish a WebRTC connection to the LiveKit server and subscribe to the agent's audio track

#### Scenario: Development environment URL
- **WHEN** the app runs in development mode (Vite dev server)
- **THEN** the LiveKit signaling URL SHALL use the Vite proxy path to reach LiveKit through Caddy

### Requirement: Room connection state display
The system SHALL display the current connection state to the user: `connecting`, `connected`, `reconnecting`, `disconnected`. The state SHALL be derived from the `useConnectionState` hook provided by `@livekit/components-react`.

#### Scenario: Connecting state
- **WHEN** the LiveKit room is in the process of connecting
- **THEN** the system SHALL display a "connecting" indicator

#### Scenario: Connected state
- **WHEN** the LiveKit room connection is established
- **THEN** the system SHALL display the chat interface with voice and text controls

#### Scenario: Reconnecting state
- **WHEN** the LiveKit connection drops and the SDK attempts reconnection
- **THEN** the system SHALL display a "reconnecting" indicator overlay

#### Scenario: Disconnected state
- **WHEN** the LiveKit connection is lost and cannot be restored
- **THEN** the system SHALL display a "disconnected" message with a reconnect option

### Requirement: Room cleanup on unmount
The system SHALL disconnect from the LiveKit room when the chat page component unmounts (e.g., on logout or navigation away). The `LiveKitRoom` component SHALL handle this automatically via its `connect` prop or unmount behavior.

#### Scenario: Logout triggers disconnect
- **WHEN** the user logs out and the chat page unmounts
- **THEN** the LiveKit room connection SHALL be closed and all tracks released

#### Scenario: Browser tab close
- **WHEN** the user closes the browser tab while connected
- **THEN** the LiveKit SDK SHALL clean up the connection (best-effort)

### Requirement: LiveKit URL configuration
The system SHALL determine the LiveKit WebSocket URL using the following priority: (1) `VITE_LIVEKIT_URL` environment variable if set, (2) constructed from `window.location` as `ws(s)://<host>/livekit-signaling/`. This allows overriding in environments where Caddy proxy is not available.

#### Scenario: Environment variable set
- **WHEN** `VITE_LIVEKIT_URL` is defined
- **THEN** the system SHALL use its value as the LiveKit signaling URL

#### Scenario: Environment variable not set
- **WHEN** `VITE_LIVEKIT_URL` is not defined
- **THEN** the system SHALL construct the URL from `window.location.protocol` (wss for https, ws for http) and `window.location.host` with path `/livekit-signaling/`

### Requirement: Audio output rendering
The system SHALL render the agent's audio track using the `RoomAudioRenderer` component from `@livekit/components-react` so that the agent's voice is played through the user's speakers.

#### Scenario: Agent speaks
- **WHEN** the agent publishes an audio track
- **THEN** the system SHALL automatically play the audio through the user's default audio output device
