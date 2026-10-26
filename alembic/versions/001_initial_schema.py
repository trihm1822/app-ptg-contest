"""Initial database schema: users, projects, problems, problem_revisions

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-26 16:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)

    # 3. Create problems table (without current_revision_id FK yet)
    op.create_table(
        'problems',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('current_revision_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_problems_project_id'), 'problems', ['project_id'], unique=False)
    op.create_index(
        'uq_problems_project_slug_active',
        'problems',
        ['project_id', 'slug'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
        sqlite_where=sa.text('deleted_at IS NULL'),
    )

    # 4. Create problem_revisions table
    op.create_table(
        'problem_revisions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('problem_id', sa.Uuid(), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('statement_md', sa.Text(), nullable=False),
        sa.Column('time_limit_ms', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('memory_limit_mb', sa.Integer(), nullable=False, server_default='256'),
        sa.Column(
            'samples',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True
        ),
        sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('problem_id', 'revision_number', name='uq_problem_revisions_problem_revision')
    )
    op.create_index(op.f('ix_problem_revisions_problem_id'), 'problem_revisions', ['problem_id'], unique=False)

    # 5. Add circular foreign key for problems.current_revision_id
    op.create_foreign_key(
        'fk_problems_current_revision_id',
        'problems',
        'problem_revisions',
        ['current_revision_id'],
        ['id'],
        ondelete='SET NULL',
        use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint('fk_problems_current_revision_id', 'problems', type_='foreignkey')
    op.drop_index(op.f('ix_problem_revisions_problem_id'), table_name='problem_revisions')
    op.drop_table('problem_revisions')
    op.drop_index('uq_problems_project_slug_active', table_name='problems')
    op.drop_index(op.f('ix_problems_project_id'), table_name='problems')
    op.drop_table('problems')
    op.drop_index(op.f('ix_projects_user_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
