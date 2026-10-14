"""Create initial schema with all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-04-17 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=128), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_created', 'sources', ['user_id', 'created_at'])
    op.create_index(op.f('ix_sources_user_id'), 'sources', ['user_id'])

    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('cron_expression', sa.String(length=255), nullable=False),
        sa.Column('timezone', sa.String(length=100), nullable=False, server_default='UTC'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('max_articles', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_next_run', 'schedules', ['user_id', 'next_run_at'])
    op.create_index(op.f('ix_schedules_user_id'), 'schedules', ['user_id'])

    # Create schedule_sources junction table
    op.create_table(
        'schedule_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schedule_id', 'source_id')
    )

    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    op.create_index('idx_source_published', 'articles', ['source_id', 'published_at'])
    op.create_index(op.f('ix_articles_source_id'), 'articles', ['source_id'])

    # Create digests table
    op.create_table(
        'digests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='generated'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_schedule_created', 'digests', ['schedule_id', 'created_at'])
    op.create_index(op.f('ix_digests_schedule_id'), 'digests', ['schedule_id'])

    # Create delivery_channels table
    op.create_table(
        'delivery_channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('config', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_channels_schedule_id'), 'delivery_channels', ['schedule_id'])

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_schedule_status', 'jobs', ['schedule_id', 'status'])
    op.create_index(op.f('ix_jobs_schedule_id'), 'jobs', ['schedule_id'])

def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('delivery_channels')
    op.drop_table('digests')
    op.drop_table('articles')
    op.drop_table('schedule_sources')
    op.drop_table('schedules')
    op.drop_table('sources')
    op.drop_table('users')
