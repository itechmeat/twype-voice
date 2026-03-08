## ADDED Requirements

### Requirement: Web App Manifest file
The application SHALL include a valid Web App Manifest (`manifest.webmanifest`) that enables browser install prompts and defines the installed app appearance.

The manifest SHALL include:
- `name`: "Twype" (full name)
- `short_name`: "Twype" (for home screen)
- `description`: app description in English
- `start_url`: "/"
- `scope`: "/"
- `display`: "standalone"
- `orientation`: "portrait"
- `theme_color` and `background_color`: matching the app's design system
- `lang`: "en"
- `icons`: array with required sizes

#### Scenario: Manifest is served correctly
- **WHEN** a browser requests `/manifest.webmanifest`
- **THEN** the server responds with a valid JSON manifest with `Content-Type: application/manifest+json`

#### Scenario: Install prompt eligibility
- **WHEN** a user visits the app in Chrome/Edge on Android or desktop
- **THEN** the browser's install criteria are met (valid manifest, registered service worker, served over HTTPS)

### Requirement: PWA icon set
The application SHALL provide icons in the following sizes and configurations:
- 192x192 PNG (for Android home screen)
- 512x512 PNG (for Android splash screen)
- 192x192 maskable PNG (for adaptive icons on Android)
- 512x512 maskable PNG (for adaptive icons on Android)
- 180x180 PNG (for Apple Touch Icon)

All icons SHALL be placed in the `public/` directory and referenced in the manifest.

#### Scenario: Icons render on Android home screen
- **WHEN** a user installs the PWA on Android
- **THEN** the home screen displays the 192x192 icon with correct padding and no clipping

#### Scenario: Apple Touch Icon
- **WHEN** a user adds the app to the iOS home screen via Safari
- **THEN** the 180x180 Apple Touch Icon is displayed

### Requirement: HTML meta tags for PWA
The `index.html` SHALL include the following meta tags:
- `<link rel="manifest" href="/manifest.webmanifest">`
- `<meta name="theme-color" content="...">` matching the manifest theme_color
- `<meta name="description" content="...">`
- `<link rel="apple-touch-icon" href="/apple-touch-icon-180x180.png">`
- `<meta name="apple-mobile-web-app-capable" content="yes">`
- `<meta name="apple-mobile-web-app-status-bar-style" content="default">`

#### Scenario: Meta tags present in production HTML
- **WHEN** the production build is served
- **THEN** all PWA meta tags are present in the `<head>` of the HTML document

#### Scenario: Theme color matches across manifest and meta
- **WHEN** the app is loaded
- **THEN** the `theme-color` meta tag value matches the `theme_color` in the manifest
