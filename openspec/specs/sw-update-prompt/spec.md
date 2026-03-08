## ADDED Requirements

### Requirement: Update prompt component

The system SHALL provide an `UpdatePrompt` React component that renders a non-intrusive banner at the top of the screen when a new Service Worker version is available. The banner SHALL include an "Update" button and a "Later" button.

#### Scenario: New version available
- **WHEN** the Service Worker detects a new version is waiting to activate
- **THEN** the UpdatePrompt banner appears at the top of the screen
- **AND** the banner does not block user interaction with the app

#### Scenario: User clicks Update
- **WHEN** the user clicks the "Update" button
- **THEN** the waiting Service Worker is activated
- **AND** the page reloads to apply the update

#### Scenario: User clicks Later
- **WHEN** the user clicks the "Later" button
- **THEN** the banner is dismissed
- **AND** the banner reappears on the next page focus or navigation event

### Requirement: SW registration uses prompt mode

The system SHALL register the Service Worker using the `useRegisterSW` hook from `virtual:pwa-register/react` with prompt-based update detection instead of the immediate `registerSW` call.

#### Scenario: Registration in production
- **WHEN** the app loads in production mode
- **THEN** the Service Worker is registered with `onNeedRefresh` and `onOfflineReady` callbacks
- **AND** no `skipWaiting` or `clientsClaim` is invoked automatically
