## ADDED Requirements

### Requirement: Mobile viewport support
The application layout SHALL be fully functional on viewports from 360px width and above. All interactive elements (buttons, text inputs, chat feed) SHALL be touch-friendly with minimum tap target size of 44x44px.

#### Scenario: App usable on 360px wide screen
- **WHEN** the app is viewed on a 360px wide viewport (e.g., small Android phone)
- **THEN** all content is visible without horizontal scrolling and all interactive elements are tappable

#### Scenario: Chat page on mobile
- **WHEN** a user opens the chat page on a mobile device
- **THEN** the chat feed takes full viewport height minus the input area, the text input is docked to the bottom, and the microphone toggle is easily reachable

### Requirement: Desktop layout adaptation
The application SHALL utilize available space on desktop viewports (1024px+) with a centered content area and appropriate max-width constraints to maintain readability.

#### Scenario: App on desktop viewport
- **WHEN** the app is viewed on a 1440px wide desktop screen
- **THEN** the main content area is centered with a max-width constraint and the layout does not stretch edge-to-edge

### Requirement: Safe area insets
The application SHALL respect safe area insets on devices with notches or rounded corners using `env(safe-area-inset-*)` CSS environment variables.

#### Scenario: Content avoids notch area
- **WHEN** the app is displayed in standalone mode on a device with a notch
- **THEN** no interactive content is obscured by the notch or system UI

### Requirement: Responsive navigation
The authentication pages and session history page SHALL adapt their layout for mobile and desktop — single column on mobile, centered card on desktop.

#### Scenario: Login page on mobile
- **WHEN** the login page is viewed on a mobile device
- **THEN** the form takes full width with appropriate padding

#### Scenario: Login page on desktop
- **WHEN** the login page is viewed on a desktop
- **THEN** the form is displayed as a centered card with constrained width
