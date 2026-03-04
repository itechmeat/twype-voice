## ADDED Requirements

### Requirement: Bearer token extraction
The system SHALL provide a FastAPI dependency `get_current_user` that extracts the Bearer token from the `Authorization` header. The dependency SHALL decode and validate the JWT token, verify `type` is `"access"`, and load the corresponding user from the database.

#### Scenario: Valid access token
- **WHEN** a request includes `Authorization: Bearer <valid_access_token>` header
- **THEN** the dependency SHALL return the `User` ORM object for the authenticated user

#### Scenario: Missing Authorization header
- **WHEN** a request to a protected endpoint has no `Authorization` header
- **THEN** the dependency SHALL raise HTTP 401 with message "Not authenticated"

#### Scenario: Invalid token format
- **WHEN** the `Authorization` header does not start with "Bearer " or the token is malformed
- **THEN** the dependency SHALL raise HTTP 401 with message "Invalid authentication credentials"

#### Scenario: Expired access token
- **WHEN** a request includes an expired access token
- **THEN** the dependency SHALL raise HTTP 401 with message "Token has expired"

#### Scenario: Refresh token used as access token
- **WHEN** a refresh token is passed in the Authorization header to a protected endpoint
- **THEN** the dependency SHALL raise HTTP 401 with message "Invalid token type"

#### Scenario: User not found
- **WHEN** a valid JWT is presented but the user no longer exists in the database
- **THEN** the dependency SHALL raise HTTP 401 with message "User not found"

### Requirement: Verified user enforcement
The `get_current_user` dependency SHALL verify that the authenticated user has `is_verified = true`. Unverified users SHALL be rejected even with a valid token.

#### Scenario: Unverified user with valid token
- **WHEN** a valid access token for an unverified user is presented to a protected endpoint
- **THEN** the dependency SHALL raise HTTP 403 with message "Email not verified"

#### Scenario: Verified user access
- **WHEN** a valid access token for a verified user is presented to a protected endpoint
- **THEN** the dependency SHALL return the user object and allow the request to proceed
