"""add supervisor decision event

Revision ID: 4327922f0820
Revises: f58b68bc0080
Create Date: 2026-08-30 15:21:18.707391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4327922f0820'
down_revision: Union[str, Sequence[str], None] = 'f58b68bc0080'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE ticketeventtype "
        "ADD VALUE IF NOT EXISTS 'SUPERVISOR_DECISION'"
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
