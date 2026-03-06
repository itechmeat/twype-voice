"""Set knowledge chunk vector dimension and indexes.

Revision ID: b6a8d4f9c2e1
Revises: 1e4c9b7f6a2d
Create Date: 2026-03-06

"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "b6a8d4f9c2e1"
down_revision: str | Sequence[str] | None = "1e4c9b7f6a2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "knowledge_chunks",
        "embedding",
        existing_type=Vector(),
        type_=Vector(1536),
        existing_nullable=True,
        postgresql_using="embedding::vector(1536)",
    )
    op.create_index(
        "ix_knowledge_chunks_embedding_hnsw",
        "knowledge_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_with={"m": 16, "ef_construction": 64},
    )
    op.create_index(
        "ix_knowledge_chunks_search_vector_gin",
        "knowledge_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported")
