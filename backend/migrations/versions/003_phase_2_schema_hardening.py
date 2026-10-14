"""Phase 2 schema hardening: timezone-aware DateTime, unique constraints, indexes, updated_at

Revision ID: 003_phase_2_schema_hardening
Revises: 002_add_schedule_preferences
Create Date: 2026-04-21 17:00:00.000000

Changes:
- 2.1: All DateTime columns → DateTime(timezone=True) with timezone-aware defaults
- 2.3: articles.url: drop global unique, add composite (source_id, url)
- 2.4: sources: add UniqueConstraint(user_id, url)
- 2.6: New indexes: schedule_sources.source_id, sources(is_active, user_id)
- 2.7: updated_at columns added to sources, schedules, articles, digests, delivery_channels, jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "003_phase_2_schema_hardening"
down_revision = "002_add_schedule_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # 2.7 Add updated_at columns (where missing)
    # ========================================================================
    # Tables missing updated_at: sources, schedules, articles, digests,
    # delivery_channels, jobs. User already has it.
    for table in ['sources', 'schedules', 'articles', 'digests', 'delivery_channels', 'jobs']:
        op.add_column(
            table,
            sa.Column(
                'updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False
            )
        )

    # ========================================================================
    # 2.1 Convert all DateTime columns → DateTime(timezone=True)
    # ========================================================================
    # Users: created_at, updated_at
    op.alter_column('users', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)
    op.alter_column('users', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # Sources: created_at
    op.alter_column('sources', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # Schedules: next_run_at, last_run_at, created_at
    op.alter_column('schedules', 'next_run_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="next_run_at AT TIME ZONE 'UTC'",
                    nullable=True)
    op.alter_column('schedules', 'last_run_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="last_run_at AT TIME ZONE 'UTC'",
                    nullable=True)
    op.alter_column('schedules', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # Articles: published_at, created_at
    op.alter_column('articles', 'published_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="published_at AT TIME ZONE 'UTC'",
                    nullable=True)
    op.alter_column('articles', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # Digests: created_at
    op.alter_column('digests', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # Delivery Channels: created_at
    op.alter_column('delivery_channels', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # Jobs: started_at, completed_at, created_at
    op.alter_column('jobs', 'started_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="started_at AT TIME ZONE 'UTC'",
                    nullable=True)
    op.alter_column('jobs', 'completed_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="completed_at AT TIME ZONE 'UTC'",
                    nullable=True)
    op.alter_column('jobs', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    server_default=sa.func.now(),
                    nullable=False)

    # ========================================================================
    # 2.3 Articles: drop global unique on url, add composite (source_id, url)
    # ========================================================================
    # Cleanup duplicates before adding constraint
    op.execute("""
        DELETE FROM articles a1
        USING articles a2
        WHERE a1.id > a2.id
          AND a1.source_id = a2.source_id
          AND a1.url = a2.url
          AND a1.url IS NOT NULL
    """)

    # Drop old unique constraint on url (if exists)
    op.execute("ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_url_key")

    # Add composite unique
    op.create_unique_constraint('uq_article_source_url', 'articles', ['source_id', 'url'])

    # ========================================================================
    # 2.4 Sources: add UniqueConstraint(user_id, url)
    # ========================================================================
    # Cleanup duplicate sources per user before adding constraint
    op.execute("""
        DELETE FROM sources s1
        USING sources s2
        WHERE s1.id > s2.id
          AND s1.user_id = s2.user_id
          AND s1.url = s2.url
    """)

    op.create_unique_constraint('uq_source_user_url', 'sources', ['user_id', 'url'])

    # ========================================================================
    # 2.6 New indexes
    # ========================================================================
    op.create_index('idx_schedule_sources_source_id', 'schedule_sources', ['source_id'])
    op.create_index('idx_sources_active_user', 'sources', ['is_active', 'user_id'])

    # ========================================================================
    # Ensure is_active NOT NULL + set defaults
    # ========================================================================
    op.alter_column('sources', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default=sa.text('true'))
    op.alter_column('schedules', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default=sa.text('true'))
    op.alter_column('delivery_channels', 'is_enabled',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default=sa.text('true'))


def downgrade() -> None:
    # ========================================================================
    # Revert 2.6 Indexes
    # ========================================================================
    op.drop_index('idx_sources_active_user', table_name='sources')
    op.drop_index('idx_schedule_sources_source_id', table_name='schedule_sources')

    # ========================================================================
    # Revert 2.4 Sources unique constraint
    # ========================================================================
    op.drop_constraint('uq_source_user_url', 'sources', type_='unique')

    # ========================================================================
    # Revert 2.3 Articles unique constraint
    # ========================================================================
    op.drop_constraint('uq_article_source_url', 'articles', type_='unique')
    op.create_unique_constraint('articles_url_key', 'articles', ['url'])

    # ========================================================================
    # Revert 2.1 DateTime timezone
    # ========================================================================
    for table, col in [
        ('jobs', 'created_at'), ('jobs', 'completed_at'), ('jobs', 'started_at'),
        ('delivery_channels', 'created_at'),
        ('digests', 'created_at'),
        ('articles', 'created_at'), ('articles', 'published_at'),
        ('schedules', 'created_at'), ('schedules', 'last_run_at'), ('schedules', 'next_run_at'),
        ('sources', 'created_at'),
        ('users', 'updated_at'), ('users', 'created_at'),
    ]:
        op.alter_column(table, col,
                        type_=sa.DateTime(),
                        existing_type=sa.DateTime(timezone=True))

    # ========================================================================
    # Revert 2.7 Drop updated_at columns
    # ========================================================================
    for table in ['jobs', 'delivery_channels', 'digests', 'articles', 'schedules', 'sources']:
        op.drop_column(table, 'updated_at')
