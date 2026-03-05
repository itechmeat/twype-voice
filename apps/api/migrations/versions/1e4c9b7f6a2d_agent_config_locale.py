"""Add locale support to agent_config.

Revision ID: 1e4c9b7f6a2d
Revises: 7c4f3d2e16b1
Create Date: 2026-03-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1e4c9b7f6a2d"
down_revision: str | Sequence[str] | None = "7c4f3d2e16b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_config",
        sa.Column("locale", sa.String(length=35), server_default=sa.text("'en'"), nullable=False),
    )
    op.drop_constraint("uq_agent_config_key", "agent_config", type_="unique")
    op.create_unique_constraint("uq_agent_config_key_locale", "agent_config", ["key", "locale"])
    op.alter_column("agent_config", "locale", server_default=None)


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported")
