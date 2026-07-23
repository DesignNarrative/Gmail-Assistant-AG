"""make_message_id_unique_per_user

Revision ID: 8e7ecbf23ddb
Revises: e9d1a8855ddc
Create Date: 2026-07-23 12:42:19.784433
"""
from alembic import op
import sqlalchemy as sa


revision = '8e7ecbf23ddb'
down_revision = 'e9d1a8855ddc'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Drop the globally unique index on message_id
    op.drop_index('ix_emails_message_id', table_name='emails')
    
    # 2. Re-create the index on message_id as non-unique
    op.create_index(op.f('ix_emails_message_id'), 'emails', ['message_id'], unique=False)
    
    # 3. Create the new composite unique constraint for (user_id, message_id)
    op.create_unique_constraint('uix_user_message_id', 'emails', ['user_id', 'message_id'])


def downgrade():
    # 1. Drop the composite unique constraint
    op.drop_constraint('uix_user_message_id', 'emails', type_='unique')
    
    # 2. Drop the non-unique index on message_id
    op.drop_index('ix_emails_message_id', table_name='emails')
    
    # 3. Re-create the globally unique index on message_id
    op.create_index('ix_emails_message_id', 'emails', ['message_id'], unique=True)

