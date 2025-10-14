"""add_task_summary_column

Revision ID: 4c25fa131c17
Revises: 73fd7ef9cd8f
Create Date: 2025-10-12 16:04:29.760759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c25fa131c17'
down_revision: Union[str, None] = '73fd7ef9cd8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add task_summary column to tasks table
    op.add_column('tasks', sa.Column('task_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove task_summary column from tasks table
    op.drop_column('tasks', 'task_summary')
