## ADDED Requirements

### Requirement: Source indicator icons per structured item
Each structured response item that has a non-empty `chunk_ids` array SHALL display a clickable source indicator icon instead of the static "Source ready" badge. The icon SHALL visually represent the source type (book, video, podcast, article, post). When an item has multiple chunk IDs referencing different source types, the system SHALL display one icon per unique source type. Items with an empty `chunk_ids` array SHALL NOT display any source indicator.

#### Scenario: Single source type on an item
- **WHEN** a structured response item has `chunk_ids: ["uuid-1", "uuid-2"]` and both chunks belong to sources of type "book"
- **THEN** the item SHALL display a single book icon as a clickable source indicator

#### Scenario: Multiple source types on an item
- **WHEN** a structured response item has `chunk_ids: ["uuid-1", "uuid-2"]` where uuid-1 is a "book" source and uuid-2 is a "video" source
- **THEN** the item SHALL display a book icon and a video icon as clickable source indicators

#### Scenario: No chunk IDs on an item
- **WHEN** a structured response item has `chunk_ids: []`
- **THEN** no source indicator icon SHALL be displayed for that item

### Requirement: Source detail popup on indicator click
When the user clicks a source indicator icon, the system SHALL display a popup or drawer showing the full source metadata fetched from the `POST /sources/resolve` endpoint. The popup SHALL display: title (always), source type (always), author (if present), section (if present), page range (if present), and URL as a clickable link (if present). Fields that are null SHALL be omitted from the display.

#### Scenario: Popup displays full metadata
- **WHEN** the user clicks a source indicator icon for an item with chunk IDs
- **THEN** the system SHALL call `POST /sources/resolve` with those chunk IDs and display a popup containing the resolved source metadata for each returned item

#### Scenario: Popup with all fields populated
- **WHEN** the resolved source has `source_type: "book"`, `title: "Medical Guide"`, `author: "Dr. Smith"`, `section: "Chapter 3"`, `page_range: "45-47"`, `url: null`
- **THEN** the popup SHALL display title "Medical Guide", type "book", author "Dr. Smith", section "Chapter 3", page range "45-47", and SHALL NOT display a URL link

#### Scenario: Popup with URL present
- **WHEN** the resolved source has a non-null `url` field
- **THEN** the popup SHALL display the URL as a clickable external link that opens in a new tab

#### Scenario: Multiple sources in popup
- **WHEN** the item's chunk IDs resolve to multiple source items
- **THEN** the popup SHALL display each source as a separate entry, grouped or listed clearly

### Requirement: Source resolution caching
The system SHALL cache resolved source metadata on the client to avoid redundant API calls. If the same set of chunk IDs has already been resolved during the current session, the cached result SHALL be used instead of making another `POST /sources/resolve` request.

#### Scenario: First click resolves from API
- **WHEN** the user clicks a source indicator for chunk IDs that have not been resolved yet
- **THEN** the system SHALL call `POST /sources/resolve` and cache the result

#### Scenario: Subsequent click uses cache
- **WHEN** the user clicks the same source indicator again (or another indicator sharing the same chunk IDs)
- **THEN** the system SHALL display the cached metadata without making an additional API call

### Requirement: Source resolution loading state
While the `POST /sources/resolve` request is in flight, the popup SHALL display a loading indicator. If the request fails, the popup SHALL display an error message with an option to retry.

#### Scenario: Loading state shown
- **WHEN** the user clicks a source indicator and the API request is in progress
- **THEN** the popup SHALL display a loading indicator

#### Scenario: Error state with retry
- **WHEN** the `POST /sources/resolve` request fails
- **THEN** the popup SHALL display an error message and a retry button that re-triggers the request

### Requirement: Popup dismissal
The source detail popup SHALL be dismissible by clicking outside the popup area, pressing the Escape key, or clicking a close button within the popup.

#### Scenario: Dismiss by clicking outside
- **WHEN** the popup is open and the user clicks outside its bounds
- **THEN** the popup SHALL close

#### Scenario: Dismiss by Escape key
- **WHEN** the popup is open and the user presses the Escape key
- **THEN** the popup SHALL close

#### Scenario: Dismiss by close button
- **WHEN** the popup is open and the user clicks the close button
- **THEN** the popup SHALL close

### Requirement: API client method for source resolution
The API client SHALL provide a `resolveSources` method that accepts an array of chunk ID strings and returns the resolved source items. The method SHALL call `POST /sources/resolve` with the chunk IDs in the request body. The method SHALL use the existing `apiFetch` function with JWT authentication.

#### Scenario: Successful resolution
- **WHEN** `resolveSources(["uuid-1", "uuid-2"])` is called
- **THEN** the method SHALL send `POST /api/sources/resolve` with body `{ "chunk_ids": ["uuid-1", "uuid-2"] }` and return the `items` array from the response

#### Scenario: Empty chunk IDs
- **WHEN** `resolveSources([])` is called
- **THEN** the method SHALL return an empty array without making an API call
