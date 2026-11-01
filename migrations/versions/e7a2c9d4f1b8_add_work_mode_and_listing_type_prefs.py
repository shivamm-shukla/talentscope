"""add work_modes and listing_types to user_preferences

Revision ID: e7a2c9d4f1b8
Revises: d1e5f9a3c7b2
Create Date: 2026-11-01 22:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "e7a2c9d4f1b8"
down_revision = "d1e5f9a3c7b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default backfills existing rows; the ORM default covers new ones.
    op.add_column(
        "user_preferences",
        sa.Column("work_modes", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "user_preferences",
        sa.Column("listing_types", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "listing_types")
    op.drop_column("user_preferences", "work_modes")
