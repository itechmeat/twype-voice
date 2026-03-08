## ADDED Requirements

### Requirement: Browser router setup
The system SHALL use React Router's `createBrowserRouter` to define application routes. The router SHALL be rendered via `<RouterProvider>` in the app entry point.

#### Scenario: Router renders
- **WHEN** the application loads
- **THEN** React Router SHALL handle URL-based navigation and render the matched route component

### Requirement: Public route layout
The system SHALL provide a `PublicLayout` route wrapper for unauthenticated pages (`/login`, `/register`, `/verify`). If the user is already authenticated (access token present in `localStorage`), `PublicLayout` SHALL redirect to `/`.

#### Scenario: Unauthenticated user visits public route
- **WHEN** an unauthenticated user navigates to `/login`
- **THEN** the login page SHALL render normally

#### Scenario: Authenticated user visits public route
- **WHEN** an authenticated user navigates to `/login`
- **THEN** the system SHALL redirect to `/`

### Requirement: Protected route layout
The system SHALL provide a `ProtectedLayout` route wrapper for authenticated pages. If the user is not authenticated (no access token in `localStorage`), `ProtectedLayout` SHALL redirect to `/login`. The layout SHALL render a base app shell with an `<Outlet />` for child routes.

#### Scenario: Authenticated user visits protected route
- **WHEN** an authenticated user navigates to `/`
- **THEN** the protected layout SHALL render with the app shell and the matched child route

#### Scenario: Unauthenticated user visits protected route
- **WHEN** an unauthenticated user navigates to `/`
- **THEN** the system SHALL redirect to `/login`

### Requirement: Route definitions
The system SHALL define the following routes:

| Path | Layout | Component |
|------|--------|-----------|
| `/login` | PublicLayout | LoginPage |
| `/register` | PublicLayout | RegisterPage |
| `/verify` | PublicLayout | VerifyPage |
| `/` | ProtectedLayout | Home (placeholder for S22) |
| `*` | — | Redirect to `/login` |

#### Scenario: Known public route
- **WHEN** a user navigates to `/register`
- **THEN** the `RegisterPage` component SHALL render inside `PublicLayout`

#### Scenario: Known protected route
- **WHEN** an authenticated user navigates to `/`
- **THEN** the home placeholder SHALL render inside `ProtectedLayout`

#### Scenario: Unknown route
- **WHEN** a user navigates to `/nonexistent`
- **THEN** the system SHALL redirect to `/login`

### Requirement: TanStack Query provider
The system SHALL wrap the application in a `QueryClientProvider` from `@tanstack/react-query` so that all components can use `useMutation` and `useQuery` hooks for API calls.

#### Scenario: Query client available
- **WHEN** any component within the app calls `useMutation`
- **THEN** the call SHALL succeed because `QueryClientProvider` is present in the component tree

### Requirement: Vite dev proxy
The Vite dev server SHALL proxy requests matching `/api/**` to `http://localhost:8000` so that local frontend development can reach the API running in Docker without CORS configuration.

#### Scenario: Local dev API call
- **WHEN** the frontend running on `localhost:5173` makes a request to `/api/auth/login`
- **THEN** Vite SHALL proxy the request to `http://localhost:8000/auth/login`
