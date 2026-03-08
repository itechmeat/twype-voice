## Context

The Twype web application (`apps/web/`) is a React 19 SPA built with Vite 7.3 and served via Caddy in production. Currently it has no PWA capabilities — no manifest, no service worker, no mobile-optimized meta tags, and no responsive layout considerations beyond basic viewport meta. The primary use case — voice interaction with an AI agent — is inherently mobile-first, making installability and offline shell critical for user experience.

The app uses LiveKit Client SDK for WebRTC voice/text, TanStack Query for REST calls, and React Router for navigation. There is no `public/` directory yet — all assets are in `src/`.

## Goals / Non-Goals

**Goals:**
- Make the app installable as a PWA on iOS, Android, and desktop browsers
- Provide an offline shell so the app loads instantly even without network (with a graceful "offline" state for features requiring connectivity)
- Optimize the Vite production build for fast initial load and efficient caching
- Ensure responsive layout works well on mobile (360px+) and desktop viewports

**Non-Goals:**
- Full offline functionality (voice/text require a live connection — offline shell only)
- Push notifications (not in MVP scope)
- Background sync for queued messages
- Native app wrapper (Capacitor/TWA)
- Custom install prompt UI (browser default is sufficient for MVP)

## Decisions

### 1. Use `vite-plugin-pwa` with Workbox for service worker generation

**Rationale:** `vite-plugin-pwa` integrates seamlessly with Vite, generates the service worker and manifest injection automatically, and uses Google Workbox under the hood for caching strategies. Manual service worker authoring would be error-prone and harder to maintain.

**Alternatives considered:**
- Manual service worker: more control, but significantly more code to maintain and test
- `@vite-pwa/assets-generator`: useful for icon generation but `vite-plugin-pwa` handles the full lifecycle

### 2. Caching strategy: precache shell + network-first for API

**Rationale:**
- **Precache** the app shell (HTML, CSS, JS bundles, fonts, icons) — these change only on deploy and are versioned by Vite hashes
- **Network-first** for `/api/*` calls — always prefer fresh data, fall back to cache only if offline
- **Cache-first** for static assets from CDN/public (icons, images) — immutable content

This gives instant load for the app shell while ensuring API data freshness.

### 3. `generateSW` mode (not `injectManifest`)

**Rationale:** The app has no custom service worker logic needs (no push, no background sync). `generateSW` is simpler and auto-manages the precache manifest. If custom SW logic is needed later, switching to `injectManifest` is straightforward.

### 4. Icon generation approach: provide source SVG, generate sizes via build script

**Rationale:** A single source SVG in `public/` with generated PNG sizes (192x192, 512x512, maskable variants) covers all platforms. Icons are generated once and committed, not regenerated on every build.

### 5. Responsive layout via CSS — no UI framework change

**Rationale:** The app already uses custom CSS. Adding a responsive grid/flexbox system with media queries is sufficient. No need to introduce a CSS framework for this scope.

### 6. Build optimization: manual chunk splitting for key vendor libraries

**Rationale:** LiveKit SDK, React, and TanStack Query are large and stable — splitting them into separate chunks improves caching. Vite 7 handles most optimization automatically (tree-shaking, minification, asset hashing), but explicit `manualChunks` for these vendors prevents chunk invalidation cascading.

## Risks / Trade-offs

- **[Risk] Service worker caching stale HTML** → Mitigation: `vite-plugin-pwa` uses `workbox-precaching` with revision hashes; stale content is replaced on next SW activation. Configure `skipWaiting` + `clientsClaim` for immediate updates.
- **[Risk] iOS PWA limitations** → Mitigation: iOS has limited PWA support (no push, limited background). Acceptable for MVP — the core experience (voice + text) works in Safari standalone mode.
- **[Risk] Large SW precache payload** → Mitigation: only precache the app shell, not API data or dynamic content. Monitor precache size — target under 2MB.
- **[Risk] LiveKit WebRTC in standalone mode** → Mitigation: WebRTC works in standalone PWA mode on both iOS and Android. No known blockers.
