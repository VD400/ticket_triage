"""update ticket and draft event enums

Revision ID: 47fa67724fdf
Revises: 37c1d8b36015
Create Date: 2026-08-22 10:23:40.737583

"""
from alembic import op

revision = '47fa67724fdf'
down_revision = '37c1d8b36015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE ticketstatus ADD VALUE IF NOT EXISTS 'NEEDS_MANUAL_REVIEW'")
    op.execute("ALTER TYPE ticketeventtype ADD VALUE IF NOT EXISTS 'DRAFT_APPROVED'")
    op.execute("ALTER TYPE ticketeventtype ADD VALUE IF NOT EXISTS 'DRAFT_REJECTED'")


def downgrade() -> None:
    # Postgres does not support removing individual enum values directly.
    # A true downgrade would require recreating the type and migrating every
    # column that uses it. Left as a no-op.
    pass