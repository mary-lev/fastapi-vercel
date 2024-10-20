"""Add TextBooks

Revision ID: 7a9ac96f69d4
Revises: b53606cb1aa5
Create Date: 2024-10-20 04:00:44.759430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a9ac96f69d4'
down_revision: Union[str, None] = 'b53606cb1aa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('textbooks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('author', sa.String(), nullable=True),
    sa.Column('book_link', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_textbooks_author'), 'textbooks', ['author'], unique=False)
    op.create_index(op.f('ix_textbooks_book_link'), 'textbooks', ['book_link'], unique=False)
    op.create_index(op.f('ix_textbooks_id'), 'textbooks', ['id'], unique=False)
    op.create_index(op.f('ix_textbooks_title'), 'textbooks', ['title'], unique=False)
    op.create_table('textbookchapters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('content_file_md', sa.String(), nullable=True),
    sa.Column('textbook_id', sa.Integer(), nullable=False),
    sa.Column('chapter_link', sa.String(), nullable=True),
    sa.Column('chapter_title', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['textbook_id'], ['textbooks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_textbookchapters_chapter_link'), 'textbookchapters', ['chapter_link'], unique=False)
    op.create_index(op.f('ix_textbookchapters_chapter_title'), 'textbookchapters', ['chapter_title'], unique=False)
    op.create_index(op.f('ix_textbookchapters_content_file_md'), 'textbookchapters', ['content_file_md'], unique=False)
    op.create_index(op.f('ix_textbookchapters_id'), 'textbookchapters', ['id'], unique=False)
    op.create_index(op.f('ix_textbookchapters_title'), 'textbookchapters', ['title'], unique=False)
    op.create_table('lessons',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('lesson_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lessons_description'), 'lessons', ['description'], unique=False)
    op.create_index(op.f('ix_lessons_id'), 'lessons', ['id'], unique=False)
    op.create_index(op.f('ix_lessons_title'), 'lessons', ['title'], unique=False)
    op.create_table('topics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('background', sa.String(), nullable=True),
    sa.Column('objectives', sa.String(), nullable=True),
    sa.Column('content_file_md', sa.String(), nullable=True),
    sa.Column('concepts', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('lesson_id', sa.Integer(), nullable=False),
    sa.Column('topic_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topics_background'), 'topics', ['background'], unique=False)
    op.create_index(op.f('ix_topics_concepts'), 'topics', ['concepts'], unique=False)
    op.create_index(op.f('ix_topics_content_file_md'), 'topics', ['content_file_md'], unique=False)
    op.create_index(op.f('ix_topics_id'), 'topics', ['id'], unique=False)
    op.create_index(op.f('ix_topics_objectives'), 'topics', ['objectives'], unique=False)
    op.create_index(op.f('ix_topics_title'), 'topics', ['title'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_topics_title'), table_name='topics')
    op.drop_index(op.f('ix_topics_objectives'), table_name='topics')
    op.drop_index(op.f('ix_topics_id'), table_name='topics')
    op.drop_index(op.f('ix_topics_content_file_md'), table_name='topics')
    op.drop_index(op.f('ix_topics_concepts'), table_name='topics')
    op.drop_index(op.f('ix_topics_background'), table_name='topics')
    op.drop_table('topics')
    op.drop_index(op.f('ix_lessons_title'), table_name='lessons')
    op.drop_index(op.f('ix_lessons_id'), table_name='lessons')
    op.drop_index(op.f('ix_lessons_description'), table_name='lessons')
    op.drop_table('lessons')
    op.drop_index(op.f('ix_textbookchapters_title'), table_name='textbookchapters')
    op.drop_index(op.f('ix_textbookchapters_id'), table_name='textbookchapters')
    op.drop_index(op.f('ix_textbookchapters_content_file_md'), table_name='textbookchapters')
    op.drop_index(op.f('ix_textbookchapters_chapter_title'), table_name='textbookchapters')
    op.drop_index(op.f('ix_textbookchapters_chapter_link'), table_name='textbookchapters')
    op.drop_table('textbookchapters')
    op.drop_index(op.f('ix_textbooks_title'), table_name='textbooks')
    op.drop_index(op.f('ix_textbooks_id'), table_name='textbooks')
    op.drop_index(op.f('ix_textbooks_book_link'), table_name='textbooks')
    op.drop_index(op.f('ix_textbooks_author'), table_name='textbooks')
    op.drop_table('textbooks')
    # ### end Alembic commands ###
