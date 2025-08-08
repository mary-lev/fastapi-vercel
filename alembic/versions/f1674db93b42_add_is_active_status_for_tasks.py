"""Add is_active status for tasks

Revision ID: f1674db93b42
Revises: 075cf7c8045f
Create Date: 2024-10-22 22:20:50.140776

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1674db93b42"
down_revision: Union[str, None] = "075cf7c8045f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add the new column with a default value (e.g., True for active tasks)
    op.add_column("tasks", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    # Step 2: Optional - Alter the column to remove the default value (this makes it cleaner in future)
    op.alter_column("tasks", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("tasks", "is_active")
