from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import uuid
from .base import Base

class Email(Base):
    __tablename__ = 'emails'
    __table_args__ = (
        UniqueConstraint('user_id', 'message_id', name='uix_user_message_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    message_id = Column(String, index=True, nullable=False)
    thread_id = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=True)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    sender_email = Column(String, index=True, nullable=False)
    sender_name = Column(String, nullable=True)
    recipients = Column(JSONB, nullable=False)      # list of dicts: [{"name": "", "email": ""}]
    cc = Column(JSONB, default=[])                  # list of dicts
    bcc = Column(JSONB, default=[])                 # list of dicts
    date_sent = Column(DateTime, nullable=False)
    date_received = Column(DateTime, nullable=False)
    labels = Column(JSONB, default=[])              # list of gmail labels
    snippet = Column(String, nullable=True)
    has_attachments = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    is_downloaded = Column(Boolean, default=False, nullable=False)
    sync_status = Column(String, default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
