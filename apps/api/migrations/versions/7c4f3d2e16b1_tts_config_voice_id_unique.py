"""Make tts_config.voice_id unique.

Revision ID: 7c4f3d2e16b1
Revises: c9fe2269439f
Create Date: 2026-03-04

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7c4f3d2e16b1"
down_revision = "c9fe2269439f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_tts_config_voice_id", "tts_config", ["voice_id"])


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported")
