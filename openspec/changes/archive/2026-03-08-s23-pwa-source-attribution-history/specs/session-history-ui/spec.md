## ADDED Requirements

### Requirement: Session history list page
The system SHALL provide a session history page accessible via a dedicated route (e.g., `/history`). The page SHALL fetch the list of past sessions from `GET /sessions/history` and display them in reverse chronological order (most recent first). Each session entry SHALL display the session start time, end time (if available), and status.

#### Scenario: Sessions listed in reverse chronological order
- **WHEN** the user navigates to the history page and has 5 past sessions
- **THEN** the page SHALL display all 5 sessions ordered by `started_at` descending

#### Scenario: Session entry displays metadata
- **WHEN** a session has `started_at: "2026-03-07T10:00:00Z"`, `ended_at: "2026-03-07T10:30:00Z"`, `status: "completed"`
- **THEN** the entry SHALL display the formatted start time, end time, and status

#### Scenario: Session with no end time
- **WHEN** a session has `ended_at: null`
- **THEN** the entry SHALL display the start time and status, and SHALL indicate the session has no recorded end time (e.g., show "In progress" or omit end time)

#### Scenario: No sessions available
- **WHEN** the user has no past sessions
- **THEN** the page SHALL display an empty state message indicating no session history is available

### Requirement: Session history loading and error states
The session history page SHALL display a loading indicator while the `GET /sessions/history` request is in flight. If the request fails, the page SHALL display an error message with a retry option.

#### Scenario: Loading state
- **WHEN** the history page is opened and the API request is in progress
- **THEN** the page SHALL display a loading indicator

#### Scenario: Error with retry
- **WHEN** the `GET /sessions/history` request fails
- **THEN** the page SHALL display an error message and a retry button

### Requirement: Session detail view
When the user selects a session from the history list, the system SHALL navigate to a session detail view (e.g., `/history/:sessionId`). The detail view SHALL fetch messages from `GET /sessions/{id}/messages` and render them as a read-only dialogue. Each message SHALL display the role (user or agent), mode (voice or text), content text, and timestamp.

#### Scenario: Navigate to session detail
- **WHEN** the user clicks on a session entry in the history list
- **THEN** the system SHALL navigate to the session detail route with that session's ID

#### Scenario: Messages rendered as dialogue
- **WHEN** the session detail view loads messages for a session with 4 messages (2 user, 2 agent)
- **THEN** the view SHALL render all 4 messages in chronological order with visual distinction between user and agent messages

#### Scenario: Message metadata displayed
- **WHEN** a message has `role: "user"`, `mode: "voice"`, `content: "What is hypertension?"`, `created_at: "2026-03-07T10:05:00Z"`
- **THEN** the message SHALL display the role as user, mode as voice, the content text, and the formatted timestamp

### Requirement: Session detail message source indicators
Messages in the session detail view that have non-empty `source_ids` SHALL display source indicators consistent with the live chat source attribution UI. Clicking a source indicator SHALL open the same source detail popup, resolving chunk IDs via `POST /sources/resolve`.

#### Scenario: Historical message with sources
- **WHEN** a historical message has `source_ids: ["uuid-1", "uuid-2"]`
- **THEN** the message SHALL display clickable source indicator icons

#### Scenario: Historical message without sources
- **WHEN** a historical message has `source_ids: null` or `source_ids: []`
- **THEN** no source indicator SHALL be displayed for that message

### Requirement: Session detail loading and error states
The session detail view SHALL display a loading indicator while the messages request is in flight. If the request fails, the view SHALL display an error message with a retry option. If no messages are found, the view SHALL display an empty state.

#### Scenario: Loading messages
- **WHEN** the session detail view is opened and the messages request is in progress
- **THEN** the view SHALL display a loading indicator

#### Scenario: Messages request fails
- **WHEN** the `GET /sessions/{id}/messages` request fails
- **THEN** the view SHALL display an error message and a retry button

#### Scenario: No messages in session
- **WHEN** the session has no messages
- **THEN** the view SHALL display an empty state message

### Requirement: Navigation between history and session detail
The session detail view SHALL provide a back navigation element that returns the user to the session history list. The browser back button SHALL also navigate correctly between these views.

#### Scenario: Back button returns to list
- **WHEN** the user is on the session detail view and clicks the back navigation element
- **THEN** the system SHALL navigate back to the session history list page

#### Scenario: Browser back navigates correctly
- **WHEN** the user is on the session detail view and presses the browser back button
- **THEN** the browser SHALL navigate to the session history list page

### Requirement: History route registration
The router SHALL register routes for the session history list page and the session detail page. Both routes SHALL require authentication; unauthenticated users SHALL be redirected to the login page.

#### Scenario: History list route accessible
- **WHEN** an authenticated user navigates to the history route
- **THEN** the session history list page SHALL be rendered

#### Scenario: Session detail route accessible
- **WHEN** an authenticated user navigates to the session detail route with a valid session ID
- **THEN** the session detail view SHALL be rendered

#### Scenario: Unauthenticated access redirects to login
- **WHEN** an unauthenticated user navigates to either history route
- **THEN** the system SHALL redirect to the login page

### Requirement: API client methods for session history
The API client SHALL provide a `getSessionHistory` method that calls `GET /sessions/history` and returns the session list items and total count. The API client SHALL also provide a `getSessionMessages` method that accepts a session ID and calls `GET /sessions/{id}/messages`, returning the list of message items. Both methods SHALL use the existing `apiFetch` function with JWT authentication.

#### Scenario: Fetch session history
- **WHEN** `getSessionHistory()` is called
- **THEN** the method SHALL send `GET /api/sessions/history` and return an object with `items` (array of session list items) and `total` (number)

#### Scenario: Fetch session messages
- **WHEN** `getSessionMessages("session-uuid")` is called
- **THEN** the method SHALL send `GET /api/sessions/session-uuid/messages` and return the array of message items
