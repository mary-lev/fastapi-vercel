"""Add task attempt limits

Revision ID: add_task_attempt_limits
Revises: 
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_task_attempt_limits'
down_revision = 'fd8882895853'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns for attempt management
    op.add_column('tasks', sa.Column('max_attempts', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('attempt_strategy', sa.String(20), server_default='unlimited', nullable=False))
    
    # Set attempt limits based on task type
    # Code tasks: unlimited attempts (NULL max_attempts)
    op.execute("""
        UPDATE tasks 
        SET attempt_strategy = 'unlimited', max_attempts = NULL 
        WHERE type = 'code_task'
    """)
    
    # All quiz types: single attempt only
    op.execute("""
        UPDATE tasks 
        SET attempt_strategy = 'single', max_attempts = 1 
        WHERE type IN ('true_false_quiz', 'multiple_select_quiz', 'single_question_task')
    """)
    
    # Add index for performance
    op.create_index('idx_tasks_attempt_strategy', 'tasks', ['attempt_strategy'])


def downgrade():
    op.drop_index('idx_tasks_attempt_strategy', 'tasks')
    op.drop_column('tasks', 'attempt_strategy')
    op.drop_column('tasks', 'max_attempts')