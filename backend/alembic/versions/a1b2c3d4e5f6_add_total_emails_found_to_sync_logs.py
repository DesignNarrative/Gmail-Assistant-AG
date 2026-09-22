"""add_total_emails_found_to_sync_logs

Revision ID: a1b2c3d4e5f6
Revises: d5e8c1f0a2b4
Create Date: 2026-09-11 00:00:00.000000

Adds total_emails_found column to sync_logs table.
This column records how many total messages were found in Gmail during a sync run,
enabling the frontend to show progress like "50/5000 emails synced".
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd5e8c1f0a2b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'sync_logs',
        sa.Column('total_emails_found', sa.Integer(), nullable=True, server_default='0')
    )


def downgrade() -> None:
    op.drop_column('sync_logs', 'total_emails_found')
