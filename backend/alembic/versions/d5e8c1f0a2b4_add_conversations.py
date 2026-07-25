"""add_conversations_and_conversation_id

Revision ID: d5e8c1f0a2b4
Revises: c4f7a2b91e3d
Create Date: 2026-07-25 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from datetime import datetime, timezone
import uuid

revision = 'd5e8c1f0a2b4'
down_revision = 'c4f7a2b91e3d'
branch_labels = None
depends_on = None


def upgrade():
    # 1. conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    # 2. conversation_id on chat_messages
    op.add_column('chat_messages', sa.Column('conversation_id', sa.UUID(), nullable=True))
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])
    op.create_foreign_key(
        'fk_chat_messages_conversation_id',
        'chat_messages', 'conversations',
        ['conversation_id'], ['id'],
        ondelete='CASCADE',
    )

    # 3. Backfill: move each user's existing messages into one "Previous Chat"
    bind = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_rows = bind.execute(
        text("SELECT DISTINCT user_id FROM chat_messages WHERE conversation_id IS NULL")
    ).fetchall()
    for row in user_rows:
        uid = row[0]
        conv_id = uuid.uuid4()
        bind.execute(
            text(
                "INSERT INTO conversations (id, user_id, title, created_at, updated_at) "
                "VALUES (:id, :uid, :title, :ts, :ts)"
            ),
            {"id": conv_id, "uid": uid, "title": "Previous Chat", "ts": now},
        )
        bind.execute(
            text(
                "UPDATE chat_messages SET conversation_id = :cid "
                "WHERE user_id = :uid AND conversation_id IS NULL"
            ),
            {"cid": conv_id, "uid": uid},
        )


def downgrade():
    op.drop_constraint('fk_chat_messages_conversation_id', 'chat_messages', type_='foreignkey')
    op.drop_index('ix_chat_messages_conversation_id', table_name='chat_messages')
    op.drop_column('chat_messages', 'conversation_id')
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_table('conversations')
