from fastapi import APIRouter
from app.core.database import check_db_connection
from app.core.config import get_settings
from datetime import datetime, timezone

router = APIRouter()
settings = get_settings()

@router.get("/health")
async def check_health():
    db_status = await check_db_connection()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "db_connected": db_status,
        "redis_connected": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
