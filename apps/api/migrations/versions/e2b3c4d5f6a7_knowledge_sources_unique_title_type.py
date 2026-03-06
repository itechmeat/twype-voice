"""Add unique constraint for knowledge source identity.

Revision ID: e2b3c4d5f6a7
Revises: b6a8d4f9c2e1
Create Date: 2026-03-06

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2b3c4d5f6a7"
down_revision: str | Sequence[str] | None = "b6a8d4f9c2e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked_sources AS (
            SELECT
                id,
                first_value(id) OVER (
                    PARTITION BY title, source_type
                    ORDER BY created_at, id
                ) AS canonical_id
            FROM knowledge_sources
        ),
        duplicate_sources AS (
            SELECT id, canonical_id
            FROM ranked_sources
            WHERE id <> canonical_id
        )
        UPDATE knowledge_chunks AS chunk
        SET source_id = duplicate.canonical_id
        FROM duplicate_sources AS duplicate
        WHERE chunk.source_id = duplicate.id
        """
    )
    op.execute(
        """
        WITH ranked_sources AS (
            SELECT
                id,
                first_value(id) OVER (
                    PARTITION BY title, source_type
                    ORDER BY created_at, id
                ) AS canonical_id
            FROM knowledge_sources
        )
        DELETE FROM knowledge_sources AS source
        USING ranked_sources AS ranked
        WHERE source.id = ranked.id
          AND ranked.id <> ranked.canonical_id
        """
    )
    op.create_unique_constraint(
        "uq_knowledge_sources_title_source_type",
        "knowledge_sources",
        ["title", "source_type"],
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported")
