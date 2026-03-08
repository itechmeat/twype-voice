## ADDED Requirements

### Requirement: Vendor chunk splitting
The Vite production build SHALL split vendor dependencies into separate chunks:
- `react` + `react-dom` in one chunk
- `livekit-client` + `@livekit/components-react` in one chunk
- `@tanstack/react-query` in one chunk
- Remaining application code in the main chunk

This ensures that stable vendor libraries are cached independently from application code.

#### Scenario: Vendor chunks are separate files
- **WHEN** `bun run build` completes
- **THEN** the output `dist/assets/` directory contains separate chunk files for React, LiveKit, and TanStack Query

#### Scenario: App code change does not invalidate vendor cache
- **WHEN** only application source code changes and a new build is produced
- **THEN** the vendor chunk hashes remain unchanged

### Requirement: Production build size targets
The total production build size (all JS + CSS, before gzip) SHALL NOT exceed 500KB for the initial page load (excluding vendor chunks loaded on demand). Vendor chunks are loaded as needed.

#### Scenario: Build size within target
- **WHEN** `bun run build` completes
- **THEN** the main entry chunk (excluding vendor splits) is under 500KB uncompressed

### Requirement: Asset hashing for cache busting
All production build output files (JS, CSS, images) SHALL include content hashes in their filenames (Vite default behavior). The `index.html` SHALL reference the hashed filenames.

#### Scenario: Built files have content hashes
- **WHEN** `bun run build` completes
- **THEN** all output files in `dist/assets/` have content hashes in their names (e.g., `index-abc123.js`)

### Requirement: Source maps excluded from production
The production build SHALL NOT include source maps in the deployed output to reduce bundle size and prevent source code exposure.

#### Scenario: No source maps in production build
- **WHEN** `bun run build` completes
- **THEN** no `.map` files are present in the `dist/` directory
