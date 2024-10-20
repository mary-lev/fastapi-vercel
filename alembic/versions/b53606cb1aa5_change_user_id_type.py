from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b53606cb1aa5'
down_revision = '0e4ef3b0703b'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create the enum type first
    user_status_enum = sa.Enum('STUDENT', 'PROFESSOR', 'ADMIN', name='userstatus')
    user_status_enum.create(op.get_bind())  # Explicitly create the enum in the database

    # Add the new column using the created enum type
    op.add_column('users', sa.Column('status', user_status_enum, nullable=True))

    # Create index on the new column
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)

    # Create the 'courses' table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('professor_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['professor_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_description'), 'courses', ['description'], unique=False)
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_title'), 'courses', ['title'], unique=False)


def downgrade() -> None:
    # Drop the index and column in reverse order
    op.drop_index(op.f('ix_users_status'), table_name='users')
    op.drop_column('users', 'status')

    # Drop the 'courses' table
    op.drop_index(op.f('ix_courses_title'), table_name='courses')
    op.drop_index(op.f('ix_courses_id'), table_name='courses')
    op.drop_index(op.f('ix_courses_description'), table_name='courses')
    op.drop_table('courses')

    # Drop the enum type
    user_status_enum = sa.Enum('STUDENT', 'PROFESSOR', 'ADMIN', name='userstatus')
    user_status_enum.drop(op.get_bind())  # Explicitly drop the enum
