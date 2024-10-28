"""Cascade for the task deletion

Revision ID: 6d10a3de25d9
Revises: 6ea2f46bde24
Create Date: 2024-10-28 01:41:04.929293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d10a3de25d9'
down_revision: Union[str, None] = '6ea2f46bde24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('code_tasks_id_fkey', 'code_tasks', type_='foreignkey')
    op.create_foreign_key(None, 'code_tasks', 'tasks', ['id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('multiple_select_quizzes_id_fkey', 'multiple_select_quizzes', type_='foreignkey')
    op.create_foreign_key(None, 'multiple_select_quizzes', 'tasks', ['id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('single_question_tasks_id_fkey', 'single_question_tasks', type_='foreignkey')
    op.create_foreign_key(None, 'single_question_tasks', 'tasks', ['id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('task_tags_task_id_fkey', 'task_tags', type_='foreignkey')
    op.drop_constraint('task_tags_tag_id_fkey', 'task_tags', type_='foreignkey')
    op.create_foreign_key(None, 'task_tags', 'tasks', ['task_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'task_tags', 'tags', ['tag_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('true_false_quizzes_id_fkey', 'true_false_quizzes', type_='foreignkey')
    op.create_foreign_key(None, 'true_false_quizzes', 'tasks', ['id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'true_false_quizzes', type_='foreignkey')
    op.create_foreign_key('true_false_quizzes_id_fkey', 'true_false_quizzes', 'tasks', ['id'], ['id'])
    op.drop_constraint(None, 'task_tags', type_='foreignkey')
    op.drop_constraint(None, 'task_tags', type_='foreignkey')
    op.create_foreign_key('task_tags_tag_id_fkey', 'task_tags', 'tags', ['tag_id'], ['id'])
    op.create_foreign_key('task_tags_task_id_fkey', 'task_tags', 'tasks', ['task_id'], ['id'])
    op.drop_constraint(None, 'single_question_tasks', type_='foreignkey')
    op.create_foreign_key('single_question_tasks_id_fkey', 'single_question_tasks', 'tasks', ['id'], ['id'])
    op.drop_constraint(None, 'multiple_select_quizzes', type_='foreignkey')
    op.create_foreign_key('multiple_select_quizzes_id_fkey', 'multiple_select_quizzes', 'tasks', ['id'], ['id'])
    op.drop_constraint(None, 'code_tasks', type_='foreignkey')
    op.create_foreign_key('code_tasks_id_fkey', 'code_tasks', 'tasks', ['id'], ['id'])
    # ### end Alembic commands ###