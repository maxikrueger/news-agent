"""Drop duplicate unique constraints on users.email / users.username

The initial migration created both a UNIQUE constraint and a UNIQUE index
for each column. The unique indexes (ix_users_email, ix_users_username)
already enforce uniqueness, so the constraints are redundant.

Revision ID: 004_drop_dup_user_constraints
Revises: 003_phase_2_schema_hardening
"""

from alembic import op

revision = "004_drop_dup_user_constraints"
down_revision = "003_phase_2_schema_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_constraint("users_username_key", "users", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("users_username_key", "users", ["username"])
    op.create_unique_constraint("users_email_key", "users", ["email"])
