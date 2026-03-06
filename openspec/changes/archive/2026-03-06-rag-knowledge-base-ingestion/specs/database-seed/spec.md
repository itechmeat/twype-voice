## ADDED Requirements

### Requirement: Seed sample knowledge source and chunks
The seed script SHALL create a sample `knowledge_sources` record and associated `knowledge_chunks` records with pre-computed embeddings for development and testing. The sample source SHALL be a short English-language article with at least 3 chunks containing substantive content.

#### Scenario: Knowledge source seeded
- **WHEN** `python scripts/seed.py` is run
- **THEN** a `knowledge_sources` record SHALL exist with `source_type='article'`, a meaningful title, `language='en'`, and `is_active` implied by presence

#### Scenario: Knowledge chunks seeded with embeddings
- **WHEN** `python scripts/seed.py` is run
- **THEN** at least 3 `knowledge_chunks` records SHALL exist for the sample source, each with non-empty `content`, a valid `embedding` vector of dimension 1536, and a populated `search_vector`

#### Scenario: Seed is idempotent for knowledge data
- **WHEN** `python scripts/seed.py` is run twice
- **THEN** the sample knowledge source and chunks SHALL not be duplicated
