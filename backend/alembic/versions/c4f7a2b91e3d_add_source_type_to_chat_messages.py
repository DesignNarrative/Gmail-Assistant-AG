"""add_source_type_to_chat_messages

Revision ID: c4f7a2b91e3d
Revises: 98341eab16e0
Create Date: 2026-07-25 12:00:00.000000

Adds a `source_type` column to `chat_messages` so the chat UI can badge
answers as "email_grounded" vs "general_knowledge". Existing rows (all of
which were generated under the strict email-only RAG mode) back-fill to
'email_grounded' via the server default.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4f7a2b91e3d'
down_revision = '98341eab16e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'chat_messages',
        sa.Column('source_type', sa.String(), nullable=False, server_default='email_grounded')
    )


def downgrade():
    op.drop_column('chat_messages', 'source_type')
