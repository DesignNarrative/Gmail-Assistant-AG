"""add_is_downloaded_to_emails

Revision ID: 98341eab16e0
Revises: 8e7ecbf23ddb
Create Date: 2026-07-23 13:15:13.443197
"""
from alembic import op
import sqlalchemy as sa


revision = '98341eab16e0'
down_revision = '8e7ecbf23ddb'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('emails', sa.Column('is_downloaded', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    op.drop_column('emails', 'is_downloaded')

