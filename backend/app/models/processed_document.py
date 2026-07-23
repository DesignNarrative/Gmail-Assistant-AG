from sqlalchemy import Column, String, Integer, DateTime, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from .base import Base

class ProcessedDocument(Base):
    __tablename__ = 'processed_documents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attachment_id = Column(UUID(as_uuid=True), ForeignKey('attachments.id', ondelete='CASCADE'), unique=True, nullable=False)
    extracted_text = Column(Text, nullable=False)
    page_count = Column(Integer, default=1)
    processing_method = Column(String, nullable=False)  # 'direct_text' or 'ocr'
    processing_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
