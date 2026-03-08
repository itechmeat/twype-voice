## Why

The backend authentication API (registration, verification, login, token refresh) has been implemented since S03, but there is no user-facing interface to interact with it. Without auth screens, no user can access the system. S21 is the first frontend story and unblocks all subsequent PWA stories (S22-S25).

## What Changes

- Add React Router with route definitions and protected route guards
- Add TanStack Query for server state management and API calls to FastAPI auth endpoints
- Create an HTTP API client with JWT token storage, automatic refresh on 401, and redirect to login on refresh token expiration
- Build authentication pages: registration (email + password), email verification (6-digit code input), and login
- Create a base application layout (shell) that wraps authenticated routes
- Install required dependencies: `react-router`, `@tanstack/react-query`

## Capabilities

### New Capabilities
- `pwa-auth-pages`: Registration, verification, and login page components with form validation and error handling
- `pwa-api-client`: HTTP client configured for FastAPI with JWT storage, automatic token refresh on 401, and auth redirect logic
- `pwa-routing`: React Router setup with public/protected route guards and base app layout

### Modified Capabilities

## Impact

- **Code:** `apps/web/` — currently a Vite+React stub, will gain routing, API layer, and auth pages
- **Dependencies:** `react-router` and `@tanstack/react-query` added to `apps/web/package.json`
- **APIs consumed:** `POST /auth/register`, `POST /auth/verify`, `POST /auth/login`, `POST /auth/refresh` (all existing)
- **Infrastructure:** No changes — the web container already exists in Docker Compose
