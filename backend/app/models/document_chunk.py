from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
import uuid
from .base import Base

class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey('emails.id', ondelete='CASCADE'), nullable=True)
    processed_doc_id = Column(UUID(as_uuid=True), ForeignKey('processed_documents.id', ondelete='CASCADE'), nullable=True)
    attachment_id = Column(UUID(as_uuid=True), ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(384), nullable=True)  # 384-dim from BAAI/bge-small-en-v1.5
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
