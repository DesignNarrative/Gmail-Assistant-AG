from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from typing import Optional, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)

async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Record an audit log entry in PostgreSQL for security tracking and compliance.
    """
    try:
        u_id = uuid.UUID(user_id) if user_id and isinstance(user_id, str) else user_id
        entry = AuditLog(
            user_id=u_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            status=status,
            error_message=error_message,
            metadata_=metadata or {}
        )
        db.add(entry)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        await db.rollback()
