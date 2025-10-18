"""Add is_personal field to topics table

Revision ID: 6ab308773333
Revises: 4c25fa131c17
Create Date: 2025-10-17 23:20:40.093302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ab308773333'
down_revision: Union[str, None] = '4c25fa131c17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_personal column with default False
    op.add_column('topics',
        sa.Column('is_personal', sa.Boolean(),
                  nullable=False,
                  server_default='false'))

    # Add index for efficient filtering when fetching lesson data
    op.create_index('idx_topics_is_personal', 'topics', ['is_personal'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_topics_is_personal', 'topics')

    # Drop column
    op.drop_column('topics', 'is_personal')
