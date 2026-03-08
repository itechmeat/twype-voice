## 1. PWA Icons and Public Assets

- [x] 1.1 Create `apps/web/public/` directory with Twype icon source SVG
- [x] 1.2 Generate PNG icons: 192x192, 512x512, 192x192 maskable, 512x512 maskable, 180x180 Apple Touch Icon
- [x] 1.3 Place all icons in `apps/web/public/` with descriptive filenames

## 2. Vite PWA Plugin Setup

- [x] 2.1 Install `vite-plugin-pwa` as dev dependency via bun
- [x] 2.2 Configure `vite-plugin-pwa` in `vite.config.ts` with `generateSW` mode, `registerType: "autoUpdate"`, manifest fields (name, short_name, icons, theme_color, background_color, display, orientation, start_url, scope)
- [x] 2.3 Configure Workbox runtime caching rules: NetworkFirst for `/api/*` (3s timeout), CacheFirst for `/assets/*`
- [x] 2.4 Set `skipWaiting: true` and `clientsClaim: true` in Workbox options

## 3. HTML Meta Tags

- [x] 3.1 Add PWA meta tags to `apps/web/index.html`: manifest link, theme-color, description, apple-touch-icon, apple-mobile-web-app-capable, apple-mobile-web-app-status-bar-style
- [x] 3.2 Verify theme-color value matches manifest theme_color

## 4. Responsive Layout

- [x] 4.1 Add CSS for safe-area insets using `env(safe-area-inset-*)` on root layout
- [x] 4.2 Ensure chat page layout is mobile-optimized: full-height chat feed, bottom-docked input, accessible mic toggle (min 44x44px tap targets)
- [x] 4.3 Add responsive styles for auth pages: full-width on mobile, centered card on desktop (1024px+ breakpoint)
- [x] 4.4 Add max-width constraint and centering for desktop layout on session history and detail pages
- [x] 4.5 Verify no horizontal scrolling on 360px viewport across all pages

## 5. Build Optimization

- [x] 5.1 Configure `build.rollupOptions.output.manualChunks` in `vite.config.ts` to split: react+react-dom, livekit-client+@livekit/components-react, @tanstack/react-query
- [x] 5.2 Disable source maps for production build (`build.sourcemap: false`)
- [x] 5.3 Run `bun run build` and verify: separate vendor chunks, content-hashed filenames, no `.map` files, acceptable bundle size

## 6. Testing and Verification

- [x] 6.1 Run existing tests to confirm no regressions
- [x] 6.2 Verify PWA installability criteria: valid manifest, registered SW, HTTPS-ready
- [x] 6.3 Test offline shell: load app, go offline, verify app shell loads from cache with offline indicator
