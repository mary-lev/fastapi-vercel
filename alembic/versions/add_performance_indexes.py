"""Add performance optimization indexes

Revision ID: add_performance_indexes
Revises: latest
Create Date: 2025-01-17 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_performance_indexes"
down_revision = "ccf4e7b886f9"
branch_labels = None
depends_on = None


def upgrade():
    """Add performance optimization indexes"""

    # Index for hierarchical navigation queries (course -> lesson -> topic -> task)
    op.create_index("idx_lessons_course_order", "lessons", ["course_id", "lesson_order"])

    op.create_index("idx_topics_lesson_order", "topics", ["lesson_id", "topic_order"])

    op.create_index("idx_tasks_topic_order", "tasks", ["topic_id", "order"])

    # Index for user progress and activity queries
    op.create_index("idx_task_attempts_user_submitted", "task_attempts", ["user_id", "submitted_at"])

    op.create_index("idx_task_solutions_user_task_completed", "task_solutions", ["user_id", "task_id", "completed_at"])

    # Covering index for frequent task queries (includes commonly needed columns)
    op.create_index("idx_tasks_topic_covering", "tasks", ["topic_id", "type", "order"])

    # Index for analytics and statistics queries
    op.create_index("idx_task_attempts_task_successful", "task_attempts", ["task_id", "is_successful", "submitted_at"])

    # Index for user enrollment and course access patterns
    op.create_index("idx_course_enrollments_user_course", "course_enrollments", ["user_id", "course_id", "enrolled_at"])

    # Index for AI feedback queries
    op.create_index("idx_ai_feedback_user_task_created", "ai_feedback", ["user_id", "task_id", "created_at"])

    # Index for telegram integration lookups
    op.create_index("idx_users_telegram_id", "users", ["telegram_user_id"])

    # Index for internal user ID lookups (commonly used in API)
    op.create_index("idx_users_internal_user_id", "users", ["internal_user_id"])

    # Index for user status filtering
    op.create_index("idx_users_status", "users", ["status"])


def downgrade():
    """Remove performance optimization indexes"""

    # Drop all the indexes we created
    op.drop_index("idx_lessons_course_order", table_name="lessons")
    op.drop_index("idx_topics_lesson_order", table_name="topics")
    op.drop_index("idx_tasks_topic_order", table_name="tasks")
    op.drop_index("idx_task_attempts_user_submitted", table_name="task_attempts")
    op.drop_index("idx_task_solutions_user_task_completed", table_name="task_solutions")
    op.drop_index("idx_tasks_topic_covering", table_name="tasks")
    op.drop_index("idx_task_attempts_task_successful", table_name="task_attempts")
    op.drop_index("idx_course_enrollments_user_course", table_name="course_enrollments")
    op.drop_index("idx_ai_feedback_user_task_created", table_name="ai_feedback")
    op.drop_index("idx_users_telegram_id", table_name="users")
    op.drop_index("idx_users_internal_user_id", table_name="users")
    op.drop_index("idx_users_status", table_name="users")
