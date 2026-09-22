"""stub for migration d5e8c1f0a2b4 applied on personal PC

Revision ID: d5e8c1f0a2b4
Revises: 98341eab16e0
Create Date: 2026-07-24 00:00:00.000000

This is a stub for a migration that was applied on the original development PC
but whose file was not committed to the repository. The database already has
this revision applied, so this stub simply records it in the migration chain
to allow future migrations to proceed.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd5e8c1f0a2b4'
down_revision = '98341eab16e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stub — DB already has this applied. Nothing to do.
    pass


def downgrade() -> None:
    # Stub — nothing to reverse.
    pass
