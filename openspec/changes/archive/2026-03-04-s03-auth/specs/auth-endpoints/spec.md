## ADDED Requirements

### Requirement: User registration
The system SHALL accept `POST /auth/register` with `email` and `password` fields. The system SHALL validate that password is at least 8 characters. The system SHALL hash the password using bcrypt via passlib. The system SHALL generate a random 6-digit numeric verification code, store it in `users.verification_code` with `verification_expires_at` set to 10 minutes from now, and send it to the user's email via Resend. The system SHALL return 201 with a confirmation message.

#### Scenario: Successful registration
- **WHEN** a valid email and password (8+ chars) are sent to `POST /auth/register`
- **THEN** a new user record is created with `is_verified = false`, a 6-digit code is stored and emailed, and response is 201 with `{"message": "Verification code sent", "email": "<email>"}`

#### Scenario: Duplicate email
- **WHEN** a registration request is sent with an email that already exists in the database
- **THEN** the system SHALL return 409 with an error message indicating the email is already registered

#### Scenario: Password too short
- **WHEN** a registration request is sent with a password shorter than 8 characters
- **THEN** the system SHALL return 422 with a validation error

### Requirement: Email verification
The system SHALL accept `POST /auth/verify` with `email` and `code` fields. The system SHALL check the code against `users.verification_code` and ensure `verification_expires_at` has not passed. On success, the system SHALL set `is_verified = true`, clear `verification_code` and `verification_expires_at`, and return JWT access and refresh tokens.

#### Scenario: Successful verification
- **WHEN** a valid email and correct 6-digit code are sent to `POST /auth/verify` before expiration
- **THEN** the user's `is_verified` is set to true, verification fields are cleared, and response is 200 with `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

#### Scenario: Expired code
- **WHEN** a verification request is sent after the code has expired (10+ minutes)
- **THEN** the system SHALL return 400 with an error message indicating the code has expired

#### Scenario: Invalid code
- **WHEN** an incorrect code is sent to `POST /auth/verify`
- **THEN** the system SHALL return 400 with an error message indicating the code is invalid

#### Scenario: Already verified user
- **WHEN** a verification request is sent for a user who is already verified
- **THEN** the system SHALL return 400 with an error message indicating the user is already verified

### Requirement: User login
The system SHALL accept `POST /auth/login` with `email` and `password` fields. The system SHALL verify the password against the stored hash using passlib. The system SHALL only allow login for verified users. On success, the system SHALL return JWT access and refresh tokens.

#### Scenario: Successful login
- **WHEN** a verified user sends correct email and password to `POST /auth/login`
- **THEN** the system SHALL return 200 with `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

#### Scenario: Wrong password
- **WHEN** an incorrect password is sent to `POST /auth/login`
- **THEN** the system SHALL return 401 with an error message indicating invalid credentials

#### Scenario: Unverified user login
- **WHEN** an unverified user attempts to login with correct credentials
- **THEN** the system SHALL return 403 with an error message indicating the email is not verified

#### Scenario: Non-existent user
- **WHEN** login is attempted with an email that does not exist
- **THEN** the system SHALL return 401 with an error message indicating invalid credentials (same as wrong password to prevent enumeration)

### Requirement: Token refresh
The system SHALL accept `POST /auth/refresh` with a `refresh_token` field. The system SHALL validate the refresh token signature and expiration, verify token type is "refresh", and return a new access token.

#### Scenario: Successful token refresh
- **WHEN** a valid, non-expired refresh token is sent to `POST /auth/refresh`
- **THEN** the system SHALL return 200 with a new `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

#### Scenario: Expired refresh token
- **WHEN** an expired refresh token is sent to `POST /auth/refresh`
- **THEN** the system SHALL return 401 with an error message indicating the token has expired

#### Scenario: Invalid refresh token
- **WHEN** a malformed or tampered token is sent to `POST /auth/refresh`
- **THEN** the system SHALL return 401 with an error message indicating an invalid token

### Requirement: JWT token structure
The system SHALL generate JWT tokens using HS256 algorithm with `JWT_SECRET` environment variable. Access tokens SHALL have a 15-minute expiration and contain `{"sub": "<user_id>", "type": "access", "exp": <timestamp>}`. Refresh tokens SHALL have a 30-day expiration and contain `{"sub": "<user_id>", "type": "refresh", "exp": <timestamp>}`.

#### Scenario: Access token payload
- **WHEN** an access token is generated for a user
- **THEN** the token payload SHALL contain `sub` (user UUID as string), `type` = `"access"`, and `exp` set to 15 minutes from creation

#### Scenario: Refresh token payload
- **WHEN** a refresh token is generated for a user
- **THEN** the token payload SHALL contain `sub` (user UUID as string), `type` = `"refresh"`, and `exp` set to 30 days from creation
