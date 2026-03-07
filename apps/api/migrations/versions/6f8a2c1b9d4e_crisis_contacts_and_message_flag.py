"""Add crisis contacts and message crisis flag.

Revision ID: 6f8a2c1b9d4e
Revises: e2b3c4d5f6a7
Create Date: 2026-03-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6f8a2c1b9d4e"
down_revision: str | Sequence[str] | None = "e2b3c4d5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crisis_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("locale", sa.String(length=35), nullable=True),
        sa.Column("contact_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crisis_contacts"),
    )
    op.create_index(
        "ix_crisis_contacts_contact_type",
        "crisis_contacts",
        ["contact_type"],
        unique=False,
    )
    op.create_index("ix_crisis_contacts_language", "crisis_contacts", ["language"], unique=False)
    op.create_index(
        "ix_crisis_contacts_language_locale",
        "crisis_contacts",
        ["language", "locale"],
        unique=False,
    )

    op.add_column(
        "messages",
        sa.Column("is_crisis", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported")
