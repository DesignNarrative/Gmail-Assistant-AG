from app.workers.celery_app import celery_app
from app.models.user import User
from app.models.sync_log import SyncLog
from app.models.attachment import Attachment
from app.models.email import Email
from app.services.gmail.gmail_client import GmailSyncService
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, join
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


# In-memory concurrency locks to prevent overlapping duplicate tasks
_active_sync_users: set[str] = set()
_active_ocr_attachments: set[str] = set()
_active_embedding_emails: set[str] = set()


# Deprecated Celery task - keeping wrapper for interface compatibility, but core runs async
@celery_app.task(name="app.workers.sync_tasks.sync_gmail_label_task")
def sync_gmail_label_task(user_id_str: str, sync_log_id_str: str):
    logger.info(f"Starting Celery sync task wrapper for user {user_id_str}, Log ID: {sync_log_id_str}")
    asyncio.run(run_sync_gmail_label(user_id_str, sync_log_id_str))

async def run_sync_gmail_label(user_id_str: str, sync_log_id_str: str):
    """
    Continuous 50-by-50 progressive sync loop:
    1. Downloads 50 emails + attachments.
    2. Commits them safely to DB and updates live progress.
    3. Queues background OCR and AI vector embeddings.
    4. Automatically pauses 2 seconds, then drains the next 50 until 0 remain.
    5. Prioritizes brand-new incoming emails dynamically on each iteration.
    """
    if user_id_str in _active_sync_users:
        logger.info(f"Sync already actively running for user {user_id_str}. Ignoring duplicate invocation.")
        return

    _active_sync_users.add(user_id_str)
    logger.info(f"Acquired sync lock for user {user_id_str}. Running continuous sync (Log ID: {sync_log_id_str})")

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

            sync_service = GmailSyncService(db, user)
            failed_message_ids: set[str] = set()

            while True:
                batch_synced, batch_att, remaining, total_found = await sync_service.sync_batch(
                    sync_log,
                    batch_size=50,
                    failed_ids=failed_message_ids
                )
                logger.info(
                    f"User {user.email}: Batch synced {batch_synced} emails, {batch_att} attachments. "
                    f"Remaining unsynced: {remaining} (Total in label: {total_found})"
                )

                # ── Launch OCR for unprocessed attachments belonging to THIS user in background ──
                unprocessed = (await db.execute(
                    select(Attachment)
                    .join(Email, Email.id == Attachment.email_id)
                    .where(
                        Attachment.is_processed == False,
                        Email.user_id == user.id
                    )
                )).scalars().all()

                if unprocessed:
                    pending_att_ids = [str(att.id) for att in unprocessed if str(att.id) not in _active_ocr_attachments]
                    if pending_att_ids:
                        asyncio.create_task(_run_ocr_background(pending_att_ids))

                # ── Launch vector embeddings for unprocessed emails in background ──
                unprocessed_emails = (await db.execute(
                    select(Email).where(Email.user_id == user.id, Email.is_processed == False)
                )).scalars().all()

                if unprocessed_emails:
                    pending_email_ids = [str(e.id) for e in unprocessed_emails if str(e.id) not in _active_embedding_emails]
                    if pending_email_ids:
                        asyncio.create_task(_run_email_embeddings_background(pending_email_ids))

                # If no emails were synced in this batch or no unsynced emails remain in label, complete
                if batch_synced == 0 or remaining == 0:
                    logger.info(
                        f"All emails synced for user {user.email}. "
                        f"Total emails: {sync_log.emails_synced}, attachments: {sync_log.attachments_downloaded}"
                    )
                    sync_log.status = "success"
                    sync_log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    await db.commit()
                    break

                # Safe pause between 50-email batches: protects Google rate limit quota & CPU
                await asyncio.sleep(2.0)

    except Exception as e:
        logger.error(f"Continuous sync task failed: {e}", exc_info=True)
        try:
            async with SessionLocal() as db:
                sync_log = (await db.execute(select(SyncLog).where(SyncLog.id == sync_log_id))).scalars().first()
                if sync_log:
                    sync_log.status = "failed"
                    sync_log.error_message = str(e)
                    sync_log.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    await db.commit()
        except Exception as log_err:
            logger.error(f"Failed to record sync failure state: {log_err}")
    finally:
        _active_sync_users.discard(user_id_str)
        logger.info(f"Released sync lock for user {user_id_str}")
        await engine.dispose()


async def _run_ocr_background(attachment_id_list: list[str]):
    """
    Background coroutine: processes OCR for a list of attachment IDs sequentially.
    Runs independently in background, guarded against concurrent duplicate processing.
    """
    from app.workers.ocr_tasks import run_process_attachment
    logger.info(f"Background OCR worker started for {len(attachment_id_list)} attachment(s)")
    for att_id_str in attachment_id_list:
        if att_id_str in _active_ocr_attachments:
            continue
        _active_ocr_attachments.add(att_id_str)
        try:
            logger.info(f"Background OCR processing attachment {att_id_str}")
            await run_process_attachment(att_id_str)
        except Exception as e:
            logger.error(f"Background OCR failed for attachment {att_id_str}: {e}", exc_info=True)
        finally:
            _active_ocr_attachments.discard(att_id_str)
    logger.info("Background OCR batch complete")


async def _run_email_embeddings_background(email_id_list: list[str]):
    """
    Background coroutine: generates vector embeddings for a list of email IDs sequentially.
    Runs independently in background, guarded against concurrent duplicate processing.
    """
    from app.workers.embedding_tasks import run_generate_email_embeddings
    logger.info(f"Background email embedding worker started for {len(email_id_list)} email(s)")
    for email_id_str in email_id_list:
        if email_id_str in _active_embedding_emails:
            continue
        _active_embedding_emails.add(email_id_str)
        try:
            logger.info(f"Background embedding for email {email_id_str}")
            await run_generate_email_embeddings(email_id_str)
        except Exception as e:
            logger.error(f"Background embedding failed for email {email_id_str}: {e}", exc_info=True)
        finally:
            _active_embedding_emails.discard(email_id_str)
    logger.info("Background email embedding batch complete")


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
