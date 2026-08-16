"""add linkedin import

Revision ID: 324184f947b0
Revises: 1c4edeede314
Create Date: 2026-08-17 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "324184f947b0"
down_revision = "1c4edeede314"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "linkedin_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("positions", sa.JSON(), nullable=False),
        sa.Column("education", sa.JSON(), nullable=False),
        sa.Column("certifications", sa.JSON(), nullable=False),
        sa.Column("inferred_skills", sa.JSON(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("linkedin_profiles")
