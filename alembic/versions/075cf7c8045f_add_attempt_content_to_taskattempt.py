"""Add attempt_content to TaskAttempt

Revision ID: 075cf7c8045f
Revises: e79737401da2
Create Date: 2024-10-21 03:56:00.812729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '075cf7c8045f'
down_revision: Union[str, None] = 'e79737401da2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task_attempts', sa.Column('attempt_content', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('task_attempts', 'attempt_content')
    # ### end Alembic commands ###