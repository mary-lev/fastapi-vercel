"""add_file_uploads_to_task_solutions

Revision ID: b88da76973ec
Revises: 6ab308773333
Create Date: 2025-10-31 13:40:41.862413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b88da76973ec'
down_revision: Union[str, None] = '6ab308773333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add file-related columns to task_solutions
    op.add_column('task_solutions', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('task_solutions', sa.Column('file_name', sa.String(), nullable=True))
    op.add_column('task_solutions', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('task_solutions', sa.Column('file_type', sa.String(), nullable=True))

    # Add index on file_path for faster lookups
    op.create_index('idx_task_solutions_file_path', 'task_solutions', ['file_path'])


def downgrade() -> None:
    # Remove index first
    op.drop_index('idx_task_solutions_file_path', table_name='task_solutions')

    # Remove columns
    op.drop_column('task_solutions', 'file_type')
    op.drop_column('task_solutions', 'file_size')
    op.drop_column('task_solutions', 'file_name')
    op.drop_column('task_solutions', 'file_path')
