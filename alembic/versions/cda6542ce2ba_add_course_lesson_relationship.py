"""Add course lesson relationship

Revision ID: cda6542ce2ba
Revises: 2b0a135e8b59
Create Date: 2024-10-25 13:53:40.315755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cda6542ce2ba'
down_revision: Union[str, None] = '2b0a135e8b59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###