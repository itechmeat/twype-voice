## Context

The `apps/web/` application is a minimal Vite + React stub with no routing, no API layer, and no pages. The backend auth API (`/auth/register`, `/auth/verify`, `/auth/login`, `/auth/refresh`) is fully implemented (S03). Caddy proxies `/api/*` to the FastAPI container with prefix stripping, so the frontend calls `/api/auth/...` in all environments.

This is the first frontend story — it establishes patterns (routing, API client, token management) that all subsequent PWA stories will reuse.

## Goals / Non-Goals

**Goals:**
- Users can register, verify email, and log in through the browser
- JWT tokens are stored securely and refreshed transparently on 401
- Protected routes redirect unauthenticated users to login
- Establish reusable patterns: API client, auth context, route guards

**Non-Goals:**
- LiveKit integration or voice/text chat UI (S22)
- Source attribution, session history (S23)
- PWA features: service worker, manifest, offline (S24)
- Styling framework or design system selection beyond basic usable forms
- OAuth, SSO, or social login
- Password reset flow
- "Remember me" / persistent sessions beyond the refresh token

## Decisions

### D1: Token storage — `localStorage`

Store `access_token` and `refresh_token` in `localStorage`.

**Why over alternatives:**
- **`httpOnly` cookies**: Would require API changes (Set-Cookie headers, CSRF protection). The API already returns tokens in JSON response bodies. Changing this is out of scope for S21.
- **In-memory only**: Tokens lost on page refresh — poor UX for a 30-day refresh token.
- **`sessionStorage`**: Tokens lost when the tab closes — same problem.

`localStorage` is standard for SPAs consuming token-based APIs. XSS risk is mitigated by not rendering untrusted HTML (React escapes by default).

### D2: API client — thin `fetch` wrapper, not Axios

Use a custom `fetch`-based API client instead of adding Axios.

**Why:**
- `fetch` is built-in — zero bundle cost
- The client only needs: JSON serialization, base URL, auth header injection, 401 interception with token refresh, redirect on refresh failure
- Axios adds ~13KB gzipped for features we don't need (progress events, request cancellation, interceptor chains)

The client exposes a single `apiFetch(path, options)` function that all TanStack Query hooks call.

### D3: Auth state — React Context + TanStack Query

Auth state is managed via a lightweight `AuthProvider` context that exposes: `isAuthenticated`, `user` (decoded from JWT), `login()`, `logout()`, `register()`, `verify()`.

TanStack Query handles server state (mutations for auth endpoints). The auth context bridges local token state with React's render cycle.

**Why not Zustand/Jotai:**
- Auth state is a single concern (tokens + user identity) — Context is sufficient
- Adding a state manager for one slice is premature; can add later if S22+ demands it

### D4: Routing structure

```
/login          — LoginPage (public)
/register       — RegisterPage (public)
/verify         — VerifyPage (public, expects email in route state or query param)
/               — redirects to /chat (future) or shows placeholder for authenticated users
/*              — 404 / redirect to login
```

Public routes redirect to `/` if already authenticated. Protected routes redirect to `/login` if not authenticated.

React Router's `createBrowserRouter` with a layout route pattern:
- `PublicLayout` wraps auth pages (redirects if authenticated)
- `ProtectedLayout` wraps app pages (redirects if not authenticated, renders an outlet with the app shell)

### D5: Form validation — HTML5 + minimal inline checks

Use native HTML5 validation (`required`, `type="email"`, `minLength`) plus simple inline checks (password confirmation, code length). No form library.

**Why not react-hook-form / Formik:**
- Three simple forms with 2-3 fields each
- No complex validation rules, no dynamic fields
- Adding a form library for this is overhead; can introduce one if S22+ needs it

### D6: Error handling pattern

API errors follow FastAPI's `{"detail": "..."}` convention. The API client extracts the `detail` field and throws a typed `ApiError`. TanStack Query mutations surface these errors, and form components display them inline.

401 during token refresh → clear tokens, redirect to `/login`.

### D7: Vite proxy for local development

Add a Vite dev server proxy (`/api` → `http://localhost:8000`) so the frontend can be developed outside Docker with `bun run dev` while the API runs in Docker. In Docker/production, Caddy handles the proxy — no code change needed since all API calls use relative `/api/...` paths.

## Risks / Trade-offs

- **`localStorage` XSS exposure** → Acceptable for MVP. React's default escaping mitigates the main vector. Can migrate to `httpOnly` cookies in a future hardening story if needed.
- **No loading skeleton or design system** → Auth screens will be functional but unstyled beyond basic CSS. Acceptable for S21; visual polish can follow in S24 or a dedicated design story.
- **Single-tab token refresh** → If multiple tabs attempt simultaneous refresh, duplicate requests may occur. Acceptable for MVP — only one refresh token is active, and the API returns new tokens idempotently per the current implementation.
- **No rate limiting on client** → The client does not throttle repeated form submissions. The API has no rate limiting either (not in scope). Both are acceptable for MVP.
