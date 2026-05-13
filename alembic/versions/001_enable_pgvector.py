"""enable pgvector extension

Revision ID: 001
Revises:
Create Date: 2026-05-13 00:00:00.000000

"""

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP EXTENSION IF EXISTS vector")
