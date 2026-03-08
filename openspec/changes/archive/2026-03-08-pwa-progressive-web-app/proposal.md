## Why

The web application is fully functional but lacks Progressive Web App capabilities — it cannot be installed on a device home screen, has no offline shell, and is missing mobile-optimized meta tags. Converting to a PWA improves user experience on mobile devices (the primary use case for a voice AI agent), enables app-like behavior (standalone display, splash screen), and provides an offline fallback when the network is temporarily unavailable.

## What Changes

- Add a Web App Manifest (`manifest.webmanifest`) with app icons, theme color, background color, and standalone display mode
- Add a service worker that caches the application shell (HTML, CSS, JS, fonts) for offline access — network-first strategy for API calls, cache-first for static assets
- Add PWA meta tags to `index.html`: `theme-color`, `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, icon links, `description`
- Integrate `vite-plugin-pwa` for automatic service worker generation and manifest injection
- Generate PWA icon set (multiple sizes: 192x192, 512x512, maskable) and place in `public/`
- Make the layout fully responsive for mobile (small screens) and desktop browsers
- Optimize Vite production build: code splitting, asset hashing, compression hints

## Capabilities

### New Capabilities

- `pwa-manifest`: Web App Manifest configuration, icon set, and installability requirements
- `pwa-service-worker`: Service worker registration, caching strategies, and offline shell behavior
- `pwa-responsive-layout`: Responsive layout rules for mobile and desktop viewports
- `pwa-build-optimization`: Vite production build configuration — code splitting, asset optimization, compression

### Modified Capabilities

_(none — no existing spec-level requirements change)_

## Impact

- **`apps/web/package.json`**: new dependency `vite-plugin-pwa`
- **`apps/web/vite.config.ts`**: PWA plugin configuration, build optimization settings
- **`apps/web/index.html`**: meta tags, manifest link, apple touch icon links
- **`apps/web/public/`**: new directory with icons, manifest file (if not inlined by plugin)
- **`apps/web/src/`**: possible service worker registration entry point, responsive CSS adjustments
- **`docker/Dockerfile.web`** (if exists): ensure production build outputs are served correctly
