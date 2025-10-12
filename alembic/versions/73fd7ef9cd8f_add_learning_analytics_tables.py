"""add_learning_analytics_tables

Revision ID: 73fd7ef9cd8f
Revises: 774f0fe90614
Create Date: 2025-10-12 00:31:18.858080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73fd7ef9cd8f'
down_revision: Union[str, None] = '774f0fe90614'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create student_task_analysis table
    op.create_table(
        'student_task_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),

        # Attempt metadata
        sa.Column('total_attempts', sa.Integer(), nullable=False),
        sa.Column('successful_attempts', sa.Integer(), nullable=False),
        sa.Column('failed_attempts', sa.Integer(), nullable=False),
        sa.Column('first_attempt_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('last_attempt_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('final_success', sa.Boolean(), nullable=False),

        # Time gap analysis (human-readable text for LLM)
        sa.Column('attempt_time_gaps', sa.Text(), nullable=True),
        sa.Column('total_time_spent', sa.Text(), nullable=True),

        # LLM analysis (structured JSON)
        sa.Column('analysis', sa.JSON(), nullable=False),

        # Professor view only (no student_summary for task level)
        sa.Column('professor_notes', sa.Text(), nullable=True),

        # Metadata
        sa.Column('analyzed_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('llm_model', sa.String(50), nullable=True),
        sa.Column('analysis_version', sa.Integer(), nullable=False, server_default='1'),

        # Performance tracking
        sa.Column('outlier_flag', sa.Boolean(), nullable=False, server_default='false'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'task_id', name='uq_user_task_analysis')
    )

    # Create indexes for student_task_analysis
    op.create_index('idx_sta_user_course', 'student_task_analysis', ['user_id', 'course_id'])
    op.create_index('idx_sta_task', 'student_task_analysis', ['task_id'])
    op.create_index('idx_sta_analyzed_at', 'student_task_analysis', ['analyzed_at'])

    # Create student_lesson_analysis table
    op.create_table(
        'student_lesson_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),

        # Topic completion metrics
        sa.Column('total_topics', sa.Integer(), nullable=False),
        sa.Column('completed_topics', sa.Integer(), nullable=False),
        sa.Column('completion_percentage', sa.Numeric(5, 2), nullable=False),

        # Aggregated task data
        sa.Column('total_tasks', sa.Integer(), nullable=False),
        sa.Column('solved_tasks', sa.Integer(), nullable=False),
        sa.Column('total_points_available', sa.Integer(), nullable=False),
        sa.Column('points_earned', sa.Integer(), nullable=False),

        # Time analysis
        sa.Column('lesson_start_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('lesson_completion_date', sa.TIMESTAMP(), nullable=True),
        sa.Column('total_lesson_time', sa.Text(), nullable=True),

        # LLM lesson synthesis (structured JSON)
        sa.Column('analysis', sa.JSON(), nullable=False),

        # Professor view: detailed lesson assessment
        sa.Column('professor_notes', sa.Text(), nullable=True),

        # Student view: motivational lesson summary
        sa.Column('student_summary', sa.Text(), nullable=True),

        # Metadata
        sa.Column('analyzed_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('llm_model', sa.String(50), nullable=True),
        sa.Column('analysis_version', sa.Integer(), nullable=False, server_default='1'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson_analysis')
    )

    # Create indexes for student_lesson_analysis
    op.create_index('idx_sla_user_course', 'student_lesson_analysis', ['user_id', 'course_id'])
    op.create_index('idx_sla_lesson', 'student_lesson_analysis', ['lesson_id'])

    # Create student_course_profile table
    op.create_table(
        'student_course_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),

        # Overall metrics
        sa.Column('total_lessons', sa.Integer(), nullable=False),
        sa.Column('completed_lessons', sa.Integer(), nullable=False),
        sa.Column('course_completion_percentage', sa.Numeric(5, 2), nullable=False),
        sa.Column('total_course_points', sa.Integer(), nullable=False),
        sa.Column('points_earned', sa.Integer(), nullable=False),

        # Time tracking
        sa.Column('course_start_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('last_activity_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('course_completion_date', sa.TIMESTAMP(), nullable=True),
        sa.Column('total_course_time', sa.Text(), nullable=True),

        # LLM course-level profile (structured JSON)
        sa.Column('analysis', sa.JSON(), nullable=False),

        # Personalized task generation recommendations
        sa.Column('recommended_practice_areas', sa.JSON(), nullable=True),

        # Professor view: comprehensive technical profile
        sa.Column('professor_notes', sa.Text(), nullable=True),

        # Student view: congratulatory course summary for dashboard
        sa.Column('student_summary', sa.Text(), nullable=True),

        # Metadata
        sa.Column('analyzed_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('llm_model', sa.String(50), nullable=True),
        sa.Column('analysis_version', sa.Integer(), nullable=False, server_default='1'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'course_id', name='uq_user_course_profile')
    )

    # Create indexes for student_course_profile
    op.create_index('idx_scp_user', 'student_course_profile', ['user_id'])
    op.create_index('idx_scp_course', 'student_course_profile', ['course_id'])
    op.create_index('idx_scp_analyzed_at', 'student_course_profile', ['analyzed_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_scp_analyzed_at', table_name='student_course_profile')
    op.drop_index('idx_scp_course', table_name='student_course_profile')
    op.drop_index('idx_scp_user', table_name='student_course_profile')
    op.drop_table('student_course_profile')

    op.drop_index('idx_sla_lesson', table_name='student_lesson_analysis')
    op.drop_index('idx_sla_user_course', table_name='student_lesson_analysis')
    op.drop_table('student_lesson_analysis')

    op.drop_index('idx_sta_analyzed_at', table_name='student_task_analysis')
    op.drop_index('idx_sta_task', table_name='student_task_analysis')
    op.drop_index('idx_sta_user_course', table_name='student_task_analysis')
    op.drop_table('student_task_analysis')
