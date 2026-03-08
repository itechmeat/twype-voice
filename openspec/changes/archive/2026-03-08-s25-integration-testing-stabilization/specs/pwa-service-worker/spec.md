## MODIFIED Requirements

### Requirement: Service Worker update behavior

The system SHALL register the Service Worker with `registerType: "prompt"` instead of `registerType: "autoUpdate"`. The workbox configuration SHALL NOT include `skipWaiting: true` or `clientsClaim: true`. The Service Worker SHALL wait for user confirmation before activating a new version.

#### Scenario: New deployment does not force-reload
- **WHEN** a new Service Worker version is deployed
- **AND** a user has an active LiveKit session
- **THEN** the current Service Worker continues serving the active session
- **AND** the new version waits in the `waiting` state until the user confirms the update

#### Scenario: Update activates on user confirmation
- **WHEN** the user confirms the update via the UpdatePrompt component
- **THEN** the waiting Service Worker activates and the page reloads
