"""add_multi_user_isolation

Revision ID: e9d1a8855ddc
Revises: f9d1a7855ccb
Create Date: 2026-07-22 13:16:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e9d1a8855ddc'
down_revision = 'f9d1a7855ccb'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add gmail_label to users table
    op.add_column('users', sa.Column('gmail_label', sa.String(), nullable=False, server_default="Director's AI Assistant"))

    # 2. Add user_id to emails table
    op.add_column('emails', sa.Column('user_id', sa.UUID(), nullable=True))
    # Note: We will make it nullable=True initially in case there's any sync log generation, 
    # but immediately configure foreign key. Let's keep it nullable=False eventually.
    op.create_foreign_key('fk_emails_user_id', 'emails', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    # Since it's a new database, we can safely alter it to non-nullable or leave it nullable=True for flexibility.
    # Let's alter to nullable=False to enforce isolation constraint.
    # To be extremely safe during migration, let's keep it nullable=False.
    op.alter_column('emails', 'user_id', nullable=False)

    # 3. Fix document_chunks columns: make processed_doc_id and attachment_id nullable
    op.alter_column('document_chunks', 'processed_doc_id', nullable=True)
    op.alter_column('document_chunks', 'attachment_id', nullable=True)

    # 4. Add email_id and user_id columns to document_chunks table
    op.add_column('document_chunks', sa.Column('email_id', sa.UUID(), nullable=True))
    op.add_column('document_chunks', sa.Column('user_id', sa.UUID(), nullable=True))
    
    op.create_foreign_key('fk_document_chunks_email_id', 'document_chunks', 'emails', ['email_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_document_chunks_user_id', 'document_chunks', 'users', ['user_id'], ['id'], ondelete='CASCADE')

def downgrade():
    op.drop_constraint('fk_document_chunks_user_id', 'document_chunks', type_='foreignkey')
    op.drop_constraint('fk_document_chunks_email_id', 'document_chunks', type_='foreignkey')
    op.drop_column('document_chunks', 'user_id')
    op.drop_column('document_chunks', 'email_id')
    
    op.alter_column('document_chunks', 'attachment_id', nullable=False)
    op.alter_column('document_chunks', 'processed_doc_id', nullable=False)
    
    op.drop_constraint('fk_emails_user_id', 'emails', type_='foreignkey')
    op.drop_column('emails', 'user_id')
    op.drop_column('users', 'gmail_label')
