"""add github sync

Revision ID: 1c4edeede314
Revises: d77abf7eb0d0
Create Date: 2026-08-17 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "1c4edeede314"
down_revision = "d77abf7eb0d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("github_username", sa.String(length=255), nullable=True)
    )
    op.create_table(
        "github_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("repo_count", sa.Integer(), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("inferred_skills", sa.JSON(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("github_profiles")
    op.drop_column("users", "github_username")
