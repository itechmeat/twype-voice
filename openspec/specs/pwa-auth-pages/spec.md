### Requirement: Registration page
The system SHALL render a registration page at `/register` with an email field (`type="email"`, required), a password field (`minLength=8`, required), and a submit button. On successful submission to `POST /api/auth/register`, the system SHALL redirect to `/verify` passing the email. On API error, the system SHALL display the error `detail` message inline on the form.

#### Scenario: Successful registration
- **WHEN** the user enters a valid email and password (8+ chars) and submits the form
- **THEN** the system SHALL call `POST /api/auth/register` with `{ email, password }`, and on 201 redirect to `/verify` with the email available for the verification page

#### Scenario: Duplicate email error
- **WHEN** the API returns 409 with `{ "detail": "Email is already registered" }`
- **THEN** the system SHALL display "Email is already registered" as an error message on the form without navigating away

#### Scenario: Validation prevents submission
- **WHEN** the user submits with an empty email or a password shorter than 8 characters
- **THEN** the browser's native validation SHALL prevent form submission

#### Scenario: Link to login
- **WHEN** the registration page is rendered
- **THEN** a link to `/login` SHALL be visible for users who already have an account

### Requirement: Verification page
The system SHALL render a verification page at `/verify` with a 6-digit code input field (required, exactly 6 characters) and a submit button. The page SHALL display the email being verified (received from navigation state or query parameter `?email=`). On successful submission to `POST /api/auth/verify`, the system SHALL store the returned tokens and redirect to `/`.

#### Scenario: Successful verification
- **WHEN** the user enters the correct 6-digit code and submits
- **THEN** the system SHALL call `POST /api/auth/verify` with `{ email, code }`, store the returned `access_token` and `refresh_token`, and redirect to `/`

#### Scenario: Invalid code
- **WHEN** the API returns 400 with `{ "detail": "Invalid verification code" }`
- **THEN** the system SHALL display "Invalid verification code" as an error message on the form

#### Scenario: Expired code
- **WHEN** the API returns 400 with `{ "detail": "Verification code has expired" }`
- **THEN** the system SHALL display "Verification code has expired" as an error message on the form

#### Scenario: Email display
- **WHEN** the verification page is loaded with email passed via navigation state or `?email=` query parameter
- **THEN** the page SHALL display the email address to the user so they know which inbox to check

#### Scenario: No email available
- **WHEN** the verification page is loaded without an email in navigation state or query parameter
- **THEN** the system SHALL redirect to `/register`

### Requirement: Login page
The system SHALL render a login page at `/login` with an email field (`type="email"`, required), a password field (required), and a submit button. On successful submission to `POST /api/auth/login`, the system SHALL store the returned tokens and redirect to `/`. On API error, the system SHALL display the error `detail` message inline.

#### Scenario: Successful login
- **WHEN** the user enters correct email and password and submits
- **THEN** the system SHALL call `POST /api/auth/login` with `{ email, password }`, store the returned `access_token` and `refresh_token`, and redirect to `/`

#### Scenario: Invalid credentials
- **WHEN** the API returns 401 with `{ "detail": "Invalid credentials" }`
- **THEN** the system SHALL display "Invalid credentials" as an error message on the form

#### Scenario: Unverified user
- **WHEN** the API returns 403 with `{ "detail": "Email is not verified" }`
- **THEN** the system SHALL display "Email is not verified" as an error message on the form

#### Scenario: Link to register
- **WHEN** the login page is rendered
- **THEN** a link to `/register` SHALL be visible for users who do not have an account

### Requirement: Loading state during submission
The system SHALL disable the submit button and display a loading indicator while an auth form submission is in progress. This applies to registration, verification, and login forms.

#### Scenario: Submit in progress
- **WHEN** the user submits any auth form and the API call is pending
- **THEN** the submit button SHALL be disabled and a loading indicator SHALL be visible

#### Scenario: Submit completes
- **WHEN** the API call completes (success or error)
- **THEN** the submit button SHALL be re-enabled and the loading indicator SHALL be removed

### Requirement: Auth context provider
The system SHALL provide an `AuthProvider` React context that exposes `isAuthenticated` (boolean derived from token presence), and `logout()` (clears tokens and redirects to `/login`). The provider SHALL initialize auth state from `localStorage` on mount.

#### Scenario: Authenticated state on load
- **WHEN** the app loads and a valid access token exists in `localStorage`
- **THEN** `isAuthenticated` SHALL be `true`

#### Scenario: Unauthenticated state on load
- **WHEN** the app loads and no access token exists in `localStorage`
- **THEN** `isAuthenticated` SHALL be `false`

#### Scenario: Logout
- **WHEN** `logout()` is called
- **THEN** tokens SHALL be cleared from `localStorage`, `isAuthenticated` SHALL become `false`, and the browser SHALL navigate to `/login`
