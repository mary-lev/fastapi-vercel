"""Initial migration

Revision ID: 0e4ef3b0703b
Revises: e10a8dcf09c1
Create Date: 2024-10-20 03:00:10.295869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e4ef3b0703b'
down_revision: Union[str, None] = 'e10a8dcf09c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('internal_user_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('hashed_sub', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_hashed_sub'), 'users', ['hashed_sub'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_internal_user_id'), 'users', ['internal_user_id'], unique=False)
    op.drop_column('users', 'name')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_users_internal_user_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_hashed_sub'), table_name='users')
    op.drop_column('users', 'hashed_sub')
    op.drop_column('users', 'internal_user_id')
    # ### end Alembic commands ###