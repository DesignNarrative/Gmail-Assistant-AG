from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.email import Email
from app.models.thread import Thread
from app.models.attachment import Attachment
from app.models.sync_log import SyncLog
from app.workers.sync_tasks import run_sync_gmail_label
from pydantic import BaseModel, Field
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class LabelSettingsUpdate(BaseModel):
    gmail_label: str = Field(..., min_length=1, max_length=100)

@router.post("/sync/trigger")
async def trigger_gmail_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=400, 
            detail="Gmail sync is not configured. Please authorize Google OAuth first."
        )
        
    try:
        # Create a new sync log entry
        sync_log = SyncLog(
            user_id=current_user.id,
            sync_type="manual",
            status="running"
        )
        db.add(sync_log)
        await db.commit()
        await db.refresh(sync_log)
        
        # Trigger background task directly inside FastAPI's event loop
        background_tasks.add_task(run_sync_gmail_label, str(current_user.id), str(sync_log.id))
        
        return {
            "detail": "Gmail sync job successfully started in background.",
            "sync_job_id": sync_log.id,
            "status": sync_log.status,
            "started_at": sync_log.started_at
        }
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule sync job")

@router.get("/sync/status")
async def get_sync_status(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = (
            select(SyncLog)
            .where(SyncLog.user_id == current_user.id)
            .order_by(desc(SyncLog.started_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()
        return logs
    except Exception as e:
        logger.error(f"Error fetching sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sync logs")

@router.get("/sync/stats")
async def get_sync_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Total emails for this user
        emails_count_stmt = select(func.count(Email.id)).where(Email.user_id == current_user.id)
        total_emails = (await db.execute(emails_count_stmt)).scalar() or 0
        
        # Total distinct threads for this user
        threads_count_stmt = select(func.count(func.distinct(Email.thread_id))).where(Email.user_id == current_user.id)
        total_threads = (await db.execute(threads_count_stmt)).scalar() or 0
        
        # Total attachments belonging to this user's emails
        att_count_stmt = (
            select(func.count(Attachment.id))
            .join(Email, Email.id == Attachment.email_id)
            .where(Email.user_id == current_user.id)
        )
        total_attachments = (await db.execute(att_count_stmt)).scalar() or 0
        
        # Total attachment size belonging to this user's emails
        att_size_stmt = (
            select(func.sum(Attachment.file_size))
            .join(Email, Email.id == Attachment.email_id)
            .where(Email.user_id == current_user.id)
        )
        total_size_bytes = (await db.execute(att_size_stmt)).scalar() or 0
        
        # Fetch latest sync run for this user
        latest_sync_stmt = (
            select(SyncLog)
            .where(SyncLog.user_id == current_user.id)
            .order_by(desc(SyncLog.started_at))
            .limit(1)
        )
        latest_sync = (await db.execute(latest_sync_stmt)).scalars().first()
        
        return {
            "total_emails": total_emails,
            "total_threads": total_threads,
            "total_attachments": total_attachments,
            "total_size_bytes": total_size_bytes,
            "latest_sync": latest_sync
        }
    except Exception as e:
        logger.error(f"Error fetching sync stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sync statistics")

@router.put("/settings/label")
async def update_gmail_label(
    payload: LabelSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = update(User).where(User.id == current_user.id).values(gmail_label=payload.gmail_label)
        await db.execute(stmt)
        await db.commit()
        return {"detail": "Gmail sync label updated successfully.", "gmail_label": payload.gmail_label}
    except Exception as e:
        logger.error(f"Error updating Gmail sync label: {e}")
        raise HTTPException(status_code=500, detail="Failed to update sync label settings")
