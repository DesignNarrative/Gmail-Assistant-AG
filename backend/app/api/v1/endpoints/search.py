from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.email import Email
from app.models.attachment import Attachment
from app.models.processed_document import ProcessedDocument
from app.models.document_chunk import DocumentChunk
from app.models.sync_log import SyncLog
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SearchResultItem(BaseModel):
    id: str
    type: str  # 'email' or 'document'
    title: str
    snippet: str
    sender: Optional[str] = None
    date: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    email_id: Optional[str] = None

class GlobalSearchResponse(BaseModel):
    query: str
    total_results: int
    page: int
    limit: int
    results: List[SearchResultItem]

class AnalyticsSummaryResponse(BaseModel):
    total_emails: int
    total_threads: int
    total_attachments: int
    total_processed_documents: int
    total_vector_chunks: int
    document_type_breakdown: Dict[str, int]
    last_sync_status: Optional[str] = None
    last_sync_time: Optional[str] = None

@router.get("/global", response_model=GlobalSearchResponse)
async def global_search(
    q: Optional[str] = Query(None, description="Search query text"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    has_attachment: Optional[bool] = Query(None, description="Filter emails with attachments"),
    doc_type: Optional[str] = Query(None, description="Filter attachment mime_type (e.g. pdf, image)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        results: List[SearchResultItem] = []
        offset = (page - 1) * limit

        q_str = q if isinstance(q, str) and q.strip() else None
        sender_str = sender if isinstance(sender, str) and sender.strip() else None
        doc_type_str = doc_type if isinstance(doc_type, str) and doc_type.strip() else None

        query_str = f"%{q_str.strip()}%" if q_str else None

        # 1. Search Emails
        email_conditions = []
        if query_str:
            email_conditions.append(or_(
                Email.subject.ilike(query_str),
                Email.body_text.ilike(query_str),
                Email.sender_email.ilike(query_str),
                Email.sender_name.ilike(query_str)
            ))
        if sender_str:
            email_conditions.append(Email.sender_email.ilike(f"%{sender_str.strip()}%"))
        if isinstance(has_attachment, bool):
            email_conditions.append(Email.has_attachments == has_attachment)

        email_stmt = select(Email)
        if email_conditions:
            email_stmt = email_stmt.where(and_(*email_conditions))
        email_stmt = email_stmt.order_by(desc(Email.date_received)).limit(limit)

        email_rows = (await db.execute(email_stmt)).scalars().all()

        for e in email_rows:
            results.append(SearchResultItem(
                id=str(e.id),
                type="email",
                title=e.subject or "(No Subject)",
                snippet=e.snippet or (e.body_text[:180] if e.body_text else ""),
                sender=f"{e.sender_name or ''} <{e.sender_email}>".strip(),
                date=e.date_received.isoformat() if e.date_received else None,
                email_id=str(e.id)
            ))

        # 2. Search Processed Documents
        if query_str or doc_type_str:
            doc_conditions = []
            if query_str:
                doc_conditions.append(or_(
                    ProcessedDocument.extracted_text.ilike(query_str),
                    Attachment.filename.ilike(query_str)
                ))
            if doc_type_str:
                doc_conditions.append(Attachment.mime_type.ilike(f"%{doc_type_str.strip()}%"))

            doc_stmt = (
                select(ProcessedDocument, Attachment)
                .join(Attachment, Attachment.id == ProcessedDocument.attachment_id)
            )
            if doc_conditions:
                doc_stmt = doc_stmt.where(and_(*doc_conditions))
            doc_stmt = doc_stmt.order_by(desc(ProcessedDocument.created_at)).limit(limit)

            doc_rows = (await db.execute(doc_stmt)).all()

            for doc, att in doc_rows:
                # Find snippet match position
                snippet = doc.extracted_text[:200] if doc.extracted_text else ""
                if q_str and doc.extracted_text:
                    pos = doc.extracted_text.lower().find(q_str.lower())
                    if pos != -1:
                        start_pos = max(0, pos - 50)
                        end_pos = min(len(doc.extracted_text), pos + 150)
                        snippet = ("..." if start_pos > 0 else "") + doc.extracted_text[start_pos:end_pos] + "..."

                results.append(SearchResultItem(
                    id=str(doc.id),
                    type="document",
                    title=att.filename,
                    snippet=snippet,
                    date=doc.created_at.isoformat() if doc.created_at else None,
                    filename=att.filename,
                    mime_type=att.mime_type,
                    email_id=str(att.email_id)
                ))

        # Sort combined results by date
        results.sort(key=lambda x: x.date or "", reverse=True)
        paginated_results = results[offset : offset + limit]

        return GlobalSearchResponse(
            query=q or "",
            total_results=len(results),
            page=page,
            limit=limit,
            results=paginated_results
        )

    except Exception as e:
        logger.error(f"Global search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Total emails
        total_emails = (await db.execute(select(func.count(Email.id)))).scalar() or 0

        # 2. Total threads
        total_threads = (await db.execute(select(func.count(func.distinct(Email.thread_id))))).scalar() or 0

        # 3. Total attachments
        total_attachments = (await db.execute(select(func.count(Attachment.id)))).scalar() or 0

        # 4. Total processed documents
        total_processed_docs = (await db.execute(select(func.count(ProcessedDocument.id)))).scalar() or 0

        # 5. Total vector chunks
        total_vector_chunks = (await db.execute(select(func.count(DocumentChunk.id)))).scalar() or 0

        # 6. Breakdown by MIME type
        mime_rows = (await db.execute(
            select(Attachment.mime_type, func.count(Attachment.id))
            .group_by(Attachment.mime_type)
        )).all()

        breakdown = {}
        for mime, count in mime_rows:
            key = "PDF" if "pdf" in (mime or "").lower() else "Word" if "word" in (mime or "").lower() else "Image" if "image" in (mime or "").lower() else "Other"
            breakdown[key] = breakdown.get(key, 0) + count

        # 7. Last sync log
        last_log = (await db.execute(
            select(SyncLog)
            .where(SyncLog.user_id == current_user.id)
            .order_by(desc(SyncLog.started_at))
            .limit(1)
        )).scalars().first()

        last_sync_status = last_log.status if last_log else "never"
        last_sync_time = last_log.started_at.isoformat() if last_log and last_log.started_at else None

        return AnalyticsSummaryResponse(
            total_emails=total_emails,
            total_threads=total_threads,
            total_attachments=total_attachments,
            total_processed_documents=total_processed_docs,
            total_vector_chunks=total_vector_chunks,
            document_type_breakdown=breakdown,
            last_sync_status=last_sync_status,
            last_sync_time=last_sync_time
        )

    except Exception as e:
        logger.error(f"Error fetching analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics summary")
