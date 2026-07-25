from fastapi import APIRouter
from app.core.database import check_db_connection
from app.core.config import get_settings
from app.api.v1.endpoints.audit import _check_redis_status
from datetime import datetime, timezone

router = APIRouter()
settings = get_settings()

@router.get("/health")
async def check_health():
    db_status = await check_db_connection()
    redis_connected = (await _check_redis_status()) == "operational"
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "db_connected": db_status,
        "redis_connected": redis_connected,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
