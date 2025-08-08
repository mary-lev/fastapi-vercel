"""add_telegram_linking_support

Revision ID: eba6e4c05530
Revises: 8a64d7082223
Create Date: 2025-08-08 20:31:52.236081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eba6e4c05530'
down_revision: Union[str, None] = '8a64d7082223'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add telegram_user_id column to users table
    op.add_column('users', sa.Column('telegram_user_id', sa.BigInteger(), nullable=True))
    
    # Create unique index on telegram_user_id
    op.create_index('ix_users_telegram_user_id', 'users', ['telegram_user_id'], unique=True)
    
    # Create telegram_link_tokens table
    op.create_table('telegram_link_tokens',
        sa.Column('jti', sa.String(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('jti')
    )
    
    # Create index on telegram_user_id for link tokens table
    op.create_index('ix_telegram_link_tokens_telegram_user_id', 'telegram_link_tokens', ['telegram_user_id'])


def downgrade() -> None:
    # Drop telegram_link_tokens table
    op.drop_index('ix_telegram_link_tokens_telegram_user_id', table_name='telegram_link_tokens')
    op.drop_table('telegram_link_tokens')
    
    # Drop telegram_user_id column from users table
    op.drop_index('ix_users_telegram_user_id', table_name='users')
    op.drop_column('users', 'telegram_user_id')
