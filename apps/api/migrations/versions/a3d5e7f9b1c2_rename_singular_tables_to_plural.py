"""Rename agent_config and tts_config tables to plural form.

Revision ID: a3d5e7f9b1c2
Revises: 6f8a2c1b9d4e
Create Date: 2026-03-08

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d5e7f9b1c2"
down_revision: str | Sequence[str] | None = "6f8a2c1b9d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("agent_config", "agent_configs")
    op.rename_table("tts_config", "tts_configs")


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported")
