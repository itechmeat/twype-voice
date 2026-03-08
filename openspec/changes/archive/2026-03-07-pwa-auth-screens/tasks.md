## 1. Dependencies and project setup

- [x] 1.1 Install `react-router` and `@tanstack/react-query` via bun in `apps/web/`
- [x] 1.2 Add Vite dev proxy: `/api` → `http://localhost:8000` in `vite.config.ts`

## 2. API client

- [x] 2.1 Create token storage module (`lib/auth-tokens.ts`): `getTokens()`, `setTokens()`, `clearTokens()` backed by `localStorage`
- [x] 2.2 Create `ApiError` class (`lib/api-error.ts`) with `status` and `detail` fields
- [x] 2.3 Create `apiFetch()` function (`lib/api-client.ts`): base URL `/api`, JSON serialization, auth header injection, error extraction into `ApiError`
- [x] 2.4 Add 401 interceptor to `apiFetch()`: single-flight token refresh via `POST /api/auth/refresh`, retry original request on success, clear tokens + redirect to `/login` on failure

## 3. Auth context

- [x] 3.1 Create `AuthProvider` context (`lib/auth-context.tsx`): `isAuthenticated` derived from token presence, `logout()` clears tokens and navigates to `/login`
- [x] 3.2 Initialize auth state from `localStorage` on provider mount; expose `useAuth()` hook

## 4. Routing

- [x] 4.1 Create `PublicLayout` component: renders `<Outlet />` if not authenticated, redirects to `/` if authenticated
- [x] 4.2 Create `ProtectedLayout` component: renders app shell with `<Outlet />` if authenticated, redirects to `/login` if not
- [x] 4.3 Create router with `createBrowserRouter`: `/login`, `/register`, `/verify` under `PublicLayout`; `/` under `ProtectedLayout`; `*` redirects to `/login`
- [x] 4.4 Wire up `QueryClientProvider`, `AuthProvider`, and `RouterProvider` in `main.tsx` / `App.tsx`

## 5. Auth pages

- [x] 5.1 Create `RegisterPage`: email + password form, submit calls `POST /api/auth/register` via TanStack `useMutation`, on success redirect to `/verify` with email, inline error display, link to `/login`
- [x] 5.2 Create `VerifyPage`: read email from navigation state or `?email=` query param (redirect to `/register` if absent), 6-digit code input, submit calls `POST /api/auth/verify`, store tokens on success, redirect to `/`, inline error display
- [x] 5.3 Create `LoginPage`: email + password form, submit calls `POST /api/auth/login` via TanStack `useMutation`, store tokens on success, redirect to `/`, inline error display, link to `/register`
- [x] 5.4 Add loading/disabled state to submit buttons on all three pages during pending mutations

## 6. Protected home placeholder

- [x] 6.1 Create `HomePage` placeholder inside `ProtectedLayout` showing authenticated state and a logout button (will be replaced by chat UI in S22)

## 7. Tests

- [x] 7.1 Unit tests for token storage functions (`getTokens`, `setTokens`, `clearTokens`)
- [x] 7.2 Unit tests for `apiFetch`: JSON handling, auth header injection, 401 refresh flow, `ApiError` throwing
- [x] 7.3 Component tests for `RegisterPage`, `VerifyPage`, `LoginPage`: form validation, mutation calls, error display, navigation
- [x] 7.4 Component tests for route guards: `PublicLayout` redirect when authenticated, `ProtectedLayout` redirect when not authenticated
