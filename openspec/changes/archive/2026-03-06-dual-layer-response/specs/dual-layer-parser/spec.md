## ADDED Requirements

### Requirement: Parse delimiter-separated voice and text parts from LLM output
The parser module SHALL accept an async iterable of string tokens (the LLM output stream) and split it into two parts using the delimiters `---VOICE---` and `---TEXT---`. Tokens before `---TEXT---` (or after `---VOICE---` if present) SHALL be yielded as the voice part. Tokens after `---TEXT---` SHALL be accumulated as the text part. The delimiter lines themselves SHALL NOT appear in either part.

#### Scenario: Response with both parts
- **WHEN** the LLM output contains `---VOICE---\nShort answer.\n---TEXT---\n- Detail [1]\n- Detail [2]`
- **THEN** the voice part SHALL yield `"Short answer."` and the text part SHALL contain `"- Detail [1]\n- Detail [2]"`

#### Scenario: Response without delimiters
- **WHEN** the LLM output contains no `---VOICE---` or `---TEXT---` delimiters
- **THEN** the entire output SHALL be yielded as the voice part and the text part SHALL be empty

#### Scenario: Response with only TEXT delimiter
- **WHEN** the LLM output contains `Some voice text\n---TEXT---\n- Bullet point`
- **THEN** tokens before `---TEXT---` SHALL be the voice part and tokens after SHALL be the text part

#### Scenario: Empty voice part
- **WHEN** the LLM output starts with `---TEXT---\n- Only bullets`
- **THEN** the voice part SHALL be empty and the text part SHALL contain the bullet content

### Requirement: Stream voice part tokens without buffering
The parser SHALL yield voice part tokens as they arrive from the LLM stream, without waiting for the full response. This ensures the TTS pipeline can begin synthesis immediately.

#### Scenario: Voice tokens streamed incrementally
- **WHEN** the LLM emits tokens `["The ", "answer ", "is ", "simple.", "\n---TEXT---", ...]`
- **THEN** the parser SHALL yield `"The "`, `"answer "`, `"is "`, `"simple."` individually as they arrive, before the text part begins

#### Scenario: Delimiter detected mid-token
- **WHEN** a single token contains `"end.\n---TEXT---\nstart"`
- **THEN** the parser SHALL yield `"end."` as voice part and accumulate `"start"` as text part

### Requirement: Extract chunk ID references from text part
The parser SHALL extract source reference markers in the format `[N]` from text part bullet points and map them to chunk UUIDs using a provided ordered list of `RagChunk` objects. The index `N` (1-based) SHALL correspond to `chunks[N-1].chunk_id`.

#### Scenario: Valid references extracted
- **WHEN** the text part contains `"- Heart rate affects mood [1][3]"` and 3 RAG chunks were injected
- **THEN** the parsed item SHALL have `text="Heart rate affects mood"` and `chunk_ids=[chunks[0].chunk_id, chunks[2].chunk_id]`

#### Scenario: Out-of-range reference ignored
- **WHEN** the text part contains `"- Some point [5]"` but only 3 RAG chunks were injected
- **THEN** the reference `[5]` SHALL be ignored and `chunk_ids` SHALL be empty for that item

#### Scenario: No references in bullet point
- **WHEN** the text part contains `"- A reasoning point without sources"`
- **THEN** the parsed item SHALL have `chunk_ids=[]` (labeled as reasoning)

#### Scenario: No RAG chunks available
- **WHEN** the text part contains references `[1]` but the RAG chunk list is empty
- **THEN** all references SHALL be ignored and all items SHALL have `chunk_ids=[]`

### Requirement: Parse text part into structured items
The parser SHALL split the text part into individual items by line, treating lines starting with `- ` or `* ` as separate bullet points. Each item SHALL be a data object with `text` (the bullet content without the marker prefix and without `[N]` references) and `chunk_ids` (list of UUIDs). Blank lines and non-bullet lines SHALL be ignored.

#### Scenario: Multiple bullet points parsed
- **WHEN** the text part is `"- Point A [1]\n- Point B\n- Point C [2][3]"`
- **THEN** the result SHALL be 3 items with respective texts and chunk_ids

#### Scenario: Mixed bullet markers
- **WHEN** the text part contains `"- Dash point\n* Star point"`
- **THEN** both lines SHALL be parsed as items

#### Scenario: Non-bullet lines ignored
- **WHEN** the text part contains `"Some header\n- Actual point [1]\nTrailing text"`
- **THEN** only `"Actual point"` SHALL be parsed as an item

### Requirement: Return parsed result as a DualLayerResult dataclass
The parser SHALL return a `DualLayerResult` dataclass with fields: `voice_text` (str, the accumulated voice part), `text_items` (list of `TextItem` dataclasses each with `text: str` and `chunk_ids: list[UUID]`), and `all_chunk_ids` (deduplicated list of all referenced chunk UUIDs across all items).

#### Scenario: Complete result structure
- **WHEN** parsing completes with voice text and 2 text items referencing chunks
- **THEN** `DualLayerResult` SHALL have `voice_text` populated, `text_items` with 2 entries, and `all_chunk_ids` containing the union of all referenced UUIDs
