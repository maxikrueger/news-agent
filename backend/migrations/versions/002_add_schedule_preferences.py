"""Add profile and language fields to schedules table

Revision ID: 002_add_schedule_preferences
Revises: 001_initial_schema
Create Date: 2026-04-21 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_schedule_preferences"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile column to schedules table
    op.add_column(
        'schedules',
        sa.Column(
            'profile',
            sa.String(length=500),
            nullable=False,
            server_default='Allgemeine Nachrichten'
        )
    )

    # Add language column to schedules table
    op.add_column(
        'schedules',
        sa.Column(
            'language',
            sa.String(length=50),
            nullable=False,
            server_default='Deutsch'
        )
    )


def downgrade() -> None:
    op.drop_column('schedules', 'language')
    op.drop_column('schedules', 'profile')
