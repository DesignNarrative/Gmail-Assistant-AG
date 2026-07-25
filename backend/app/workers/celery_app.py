from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    # NOTE: No beat_schedule here. The single daily auto-sync runs at midnight via the
    # in-app asyncio scheduler (run_daily_sync_scheduler_task in sync_tasks.py), matching
    # the "sync once a day" requirement. A Celery beat schedule would double-sync if a
    # beat process were ever started alongside the app, so it is intentionally omitted.
)

# Auto-discover or import tasks
import app.workers.sync_tasks
import app.workers.ocr_tasks
import app.workers.embedding_tasks
