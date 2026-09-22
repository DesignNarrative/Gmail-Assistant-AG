"""make_attachment_storage_path_content_hash_nullable

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-16 00:00:00.000000

Makes storage_path and content_hash nullable on the attachments table.
This allows large attachments to be tracked in the database (metadata only)
without requiring the file to be downloaded and hashed.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('attachments', 'storage_path', existing_type=sa.String(), nullable=True)
    op.alter_column('attachments', 'content_hash', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('attachments', 'storage_path', existing_type=sa.String(), nullable=False)
    op.alter_column('attachments', 'content_hash', existing_type=sa.String(), nullable=False)
