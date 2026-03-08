### Requirement: API client base URL and JSON handling
The system SHALL provide an `apiFetch(path, options)` function that prepends `/api` to all request paths and sets `Content-Type: application/json` for requests with a body. The function SHALL serialize request bodies to JSON and deserialize JSON response bodies automatically.

#### Scenario: GET request
- **WHEN** `apiFetch("/auth/refresh", { method: "POST", body: { refresh_token: "..." } })` is called
- **THEN** the request SHALL be sent to `/api/auth/refresh` with `Content-Type: application/json` and a JSON-serialized body, and the response SHALL be parsed as JSON

#### Scenario: Request without body
- **WHEN** `apiFetch("/sessions/history")` is called without a body
- **THEN** the request SHALL be sent to `/api/sessions/history` without `Content-Type` header and without a body

### Requirement: Auth header injection
The system SHALL read the access token from `localStorage` (key `access_token`) and attach it as an `Authorization: Bearer <token>` header on every request made through `apiFetch`. If no access token is stored, the request SHALL be sent without the `Authorization` header.

#### Scenario: Authenticated request
- **WHEN** an access token exists in `localStorage` and `apiFetch` is called
- **THEN** the request SHALL include `Authorization: Bearer <access_token>` header

#### Scenario: Unauthenticated request
- **WHEN** no access token exists in `localStorage` and `apiFetch` is called
- **THEN** the request SHALL be sent without an `Authorization` header

### Requirement: Automatic token refresh on 401
When `apiFetch` receives a 401 response, the system SHALL attempt to refresh the access token by calling `POST /api/auth/refresh` with the stored refresh token. If the refresh succeeds, the system SHALL store the new tokens in `localStorage` and retry the original request with the new access token. If the refresh fails (401 or network error), the system SHALL clear both tokens from `localStorage` and redirect to `/login`.

#### Scenario: Successful automatic refresh
- **WHEN** an API call returns 401 and a valid refresh token is stored
- **THEN** the system SHALL call `POST /api/auth/refresh`, store the new tokens, and retry the original request exactly once

#### Scenario: Refresh token expired
- **WHEN** an API call returns 401 and the refresh attempt also returns 401
- **THEN** the system SHALL remove `access_token` and `refresh_token` from `localStorage` and redirect the browser to `/login`

#### Scenario: No duplicate refresh
- **WHEN** multiple concurrent API calls receive 401 simultaneously
- **THEN** only one refresh request SHALL be made; all waiting calls SHALL use the result of that single refresh

### Requirement: API error typing
The system SHALL throw an `ApiError` with `status` (HTTP status code) and `detail` (string from the response `detail` field) when the API returns a non-2xx response. If the response body does not contain a `detail` field, the `detail` SHALL default to the HTTP status text.

#### Scenario: FastAPI error response
- **WHEN** the API returns `{ "detail": "Email is already registered" }` with status 409
- **THEN** `apiFetch` SHALL throw an `ApiError` with `status: 409` and `detail: "Email is already registered"`

#### Scenario: Non-JSON error response
- **WHEN** the API returns a non-JSON response with status 500
- **THEN** `apiFetch` SHALL throw an `ApiError` with `status: 500` and `detail` set to the HTTP status text

### Requirement: Token storage functions
The system SHALL provide `getTokens()`, `setTokens(access, refresh)`, and `clearTokens()` functions for reading, writing, and removing `access_token` and `refresh_token` from `localStorage`. These functions SHALL be the only way tokens are accessed throughout the application.

#### Scenario: Store tokens after login
- **WHEN** `setTokens("abc", "xyz")` is called
- **THEN** `localStorage` SHALL contain `access_token: "abc"` and `refresh_token: "xyz"`

#### Scenario: Clear tokens on logout
- **WHEN** `clearTokens()` is called
- **THEN** both `access_token` and `refresh_token` SHALL be removed from `localStorage`
