## MODIFIED Requirements

### Requirement: Structured response rendering
When a `structured_response` message is received, the system SHALL render each item in the `items` array as a separate block. Each item SHALL display its `text` content. Items with non-empty `chunk_ids` arrays SHALL display clickable source indicator icons representing the source type (book, video, podcast, article, post) inline with the item text. The source indicator icons SHALL be rendered in place of the previous static "Source ready" badge. Clicking a source indicator icon SHALL trigger the source attribution popup as defined in the `source-attribution-ui` capability. Items with an empty `chunk_ids` array SHALL NOT display any source indicator.

#### Scenario: Items rendered as blocks
- **WHEN** a `structured_response` with 3 items is received
- **THEN** the message list SHALL render 3 distinct content blocks within one agent message

#### Scenario: Item with chunk_ids shows clickable source icons
- **WHEN** an item has `chunk_ids: ["uuid-1", "uuid-2"]`
- **THEN** the item SHALL display clickable source indicator icons inline with the item text, replacing the static badge

#### Scenario: Item without chunk_ids shows no source indicator
- **WHEN** an item has `chunk_ids: []`
- **THEN** no source indicator SHALL be displayed for that item

#### Scenario: Source icon click opens popup
- **WHEN** the user clicks a source indicator icon on a structured response item
- **THEN** the system SHALL open the source detail popup and resolve the item's chunk IDs via `POST /sources/resolve`
