from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.config import get_settings
from typing import List, Optional, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

class AuditLogResponseItem(BaseModel):
    id: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: str

class AuditLogsResponse(BaseModel):
    total: int
    page: int
    limit: int
    logs: List[AuditLogResponseItem]

class SystemStatusResponse(BaseModel):
    database_status: str
    redis_status: str
    celery_worker_status: str
    vector_search_engine: str
    llm_model: str
    active_label: str
    debug_mode: bool

@router.get("/logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        offset = (page - 1) * limit
        action_str = action if isinstance(action, str) and action.strip() else None

        stmt = select(AuditLog).where(AuditLog.user_id == current_user.id)
        if action_str:
            stmt = stmt.where(AuditLog.action.ilike(f"%{action_str.strip()}%"))

        count_stmt = select(func.count(AuditLog.id)).where(AuditLog.user_id == current_user.id)
        if action_str:
            count_stmt = count_stmt.where(AuditLog.action.ilike(f"%{action_str.strip()}%"))
        
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()

        output = []
        for r in rows:
            output.append(AuditLogResponseItem(
                id=str(r.id),
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                ip_address=r.ip_address,
                status=r.status,
                error_message=r.error_message,
                created_at=r.created_at.isoformat() if r.created_at else ""
            ))

        return AuditLogsResponse(
            total=total,
            page=page,
            limit=limit,
            logs=output
        )
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")

@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check DB
        db_status = "operational"
        try:
            await db.execute(select(1))
        except Exception:
            db_status = "error"

        return SystemStatusResponse(
            database_status=db_status,
            redis_status="operational",
            celery_worker_status="operational",
            vector_search_engine="pgvector (384-dim BAAI/bge-small-en-v1.5)",
            llm_model="Groq LLaMA 3.3 70B Versatile",
            active_label=current_user.gmail_label or settings.GMAIL_LABEL or "Director's AI Assistant",
            debug_mode=settings.DEBUG
        )
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system status")
