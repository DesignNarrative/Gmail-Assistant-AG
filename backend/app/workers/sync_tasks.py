from app.workers.celery_app import celery_app
from app.models.user import User
from app.models.sync_log import SyncLog
from app.models.attachment import Attachment
from app.services.gmail.gmail_client import GmailSyncService
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from datetime import datetime, timezone
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def get_fresh_session_factory():
    """
    Create a brand-new async engine + session factory scoped to this event loop invocation.
    This prevents the asyncpg connection pool from being shared across different asyncio.run() calls.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,
    )
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False), engine


# Deprecated Celery task - keeping wrapper for interface compatibility, but core runs async
@celery_app.task(name="app.workers.sync_tasks.sync_gmail_label_task")
def sync_gmail_label_task(user_id_str: str, sync_log_id_str: str):
    logger.info(f"Starting Celery sync task wrapper for user {user_id_str}, Log ID: {sync_log_id_str}")
    asyncio.run(run_sync_gmail_label(user_id_str, sync_log_id_str))

async def run_sync_gmail_label(user_id_str: str, sync_log_id_str: str):
    logger.info(f"Running async sync_gmail_label for user {user_id_str}, Log ID: {sync_log_id_str}")
    user_id = uuid.UUID(user_id_str)
    sync_log_id = uuid.UUID(sync_log_id_str)
    SessionLocal, engine = get_fresh_session_factory()

    try:
        async with SessionLocal() as db:
            user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
            if not user:
                logger.error(f"User {user_id_str} not found for sync task")
                return

            sync_log = (await db.execute(select(SyncLog).where(SyncLog.id == sync_log_id))).scalars().first()
            if not sync_log:
                logger.error(f"SyncLog {sync_log_id_str} not found")
                return

            try:
                sync_service = GmailSyncService(db, user)
                emails_count, att_count = await sync_service.sync_emails(sync_log)

                sync_log.status = "success"
                sync_log.emails_synced = emails_count
                sync_log.attachments_downloaded = att_count
                sync_log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
                logger.info(f"Sync completed. Emails: {emails_count}, Attachments: {att_count}")

                # After sync, run OCR + embedding for all unprocessed attachments directly in background
                if att_count > 0:
                    unprocessed = (await db.execute(
                        select(Attachment).where(Attachment.is_processed == False)
                    )).scalars().all()
                    for att in unprocessed:
                        from app.workers.ocr_tasks import run_process_attachment
                        logger.info(f"Triggering direct OCR for attachment {att.id} ({att.filename})")
                        # Run sequentially to keep CPU usage low on local laptop
                        await run_process_attachment(str(att.id))

                # Also generate email embeddings directly in background for UNPROCESSED emails
                from app.models.email import Email
                unprocessed_emails = (await db.execute(
                    select(Email).where(Email.user_id == user.id, Email.is_processed == False)
                )).scalars().all()
                for email in unprocessed_emails:
                    from app.workers.embedding_tasks import run_generate_email_embeddings
                    logger.info(f"Triggering direct email embedding for email {email.id} ({email.subject})")
                    await run_generate_email_embeddings(str(email.id))

            except Exception as e:
                logger.error(f"Sync task failed: {e}", exc_info=True)
                sync_log.status = "failed"
                sync_log.error_message = str(e)
                sync_log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
    finally:
        await engine.dispose()


# Deprecated Celery task - keeping wrapper for interface compatibility, but core runs async
@celery_app.task(name="app.workers.sync_tasks.auto_sync_all_users_task")
def auto_sync_all_users_task():
    logger.info("Starting Celery automated background Gmail sync wrapper...")
    asyncio.run(run_auto_sync_all_users())

async def run_auto_sync_all_users():
    logger.info("Running async auto_sync_all_users for all active accounts...")
    SessionLocal, engine = get_fresh_session_factory()
    try:
        async with SessionLocal() as db:
            users = (await db.execute(
                select(User).where(User.is_active == True, User.google_access_token.isnot(None))
            )).scalars().all()

            for user in users:
                sync_log = SyncLog(
                    user_id=user.id,
                    sync_type="auto",
                    status="running"
                )
                db.add(sync_log)
                await db.commit()
                await db.refresh(sync_log)
                
                # Run sync in the background of the FastAPI event loop
                asyncio.create_task(run_sync_gmail_label(str(user.id), str(sync_log.id)))
                logger.info(f"Started async auto sync task for user {user.email} (Log ID: {sync_log.id})")
    finally:
        await engine.dispose()


async def run_daily_sync_scheduler_task():
    """
    Lightweight background task running in the main event loop.
    Sleeps until midnight, then wakes up to run auto sync for all users.
    """
    from datetime import time, timedelta
    logger.info("Daily auto-sync scheduler loop started.")
    while True:
        try:
            # Calculate duration until next midnight
            now = datetime.now()
            target = datetime.combine(now.date() + timedelta(days=1), time(0, 0, 0))
            seconds_to_wait = (target - now).total_seconds()
            
            logger.info(f"Daily sync scheduler sleeping for {seconds_to_wait:.1f} seconds until midnight.")
            await asyncio.sleep(seconds_to_wait)
            
            logger.info("Waking up to trigger daily scheduled auto sync...")
            await run_auto_sync_all_users()
        except asyncio.CancelledError:
            logger.info("Daily sync scheduler task was cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in daily sync scheduler loop: {e}", exc_info=True)
            # Sleep 1 hour before retrying in case of database or system failures
            await asyncio.sleep(3600)
