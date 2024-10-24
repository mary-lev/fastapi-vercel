"""Add textbook column for the lesson

Revision ID: 7f3eb15d91cf
Revises: f1674db93b42
Create Date: 2024-10-23 00:26:13.652857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3eb15d91cf'
down_revision: Union[str, None] = 'f1674db93b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lessons', sa.Column('textbook', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('lessons', 'textbook')
    # ### end Alembic commands ###
