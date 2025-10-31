"""add_assignment_submission_table

Revision ID: 95153f8050d8
Revises: b88da76973ec
Create Date: 2025-10-31 13:55:09.176901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95153f8050d8'
down_revision: Union[str, None] = 'b88da76973ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create assignment_submissions table
    op.create_table(
        'assignment_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop assignment_submissions table
    op.drop_table('assignment_submissions')
