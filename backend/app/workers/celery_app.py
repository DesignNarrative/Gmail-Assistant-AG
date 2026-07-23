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
    beat_schedule={
        "auto-sync-gmail-every-10-min": {
            "task": "app.workers.sync_tasks.auto_sync_all_users_task",
            "schedule": 600.0,  # Every 10 minutes
        },
    }
)

# Auto-discover or import tasks
import app.workers.sync_tasks
import app.workers.ocr_tasks
import app.workers.embedding_tasks
