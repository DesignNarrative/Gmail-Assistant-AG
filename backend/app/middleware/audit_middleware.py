from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.database import AsyncSessionLocal
from app.models.audit_log import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health"):
            return await call_next(request)
            
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
        finally:
            try:
                async with AsyncSessionLocal() as db:
                    log = AuditLog(
                        action=f"{request.method} {request.url.path}",
                        ip_address=request.client.host if request.client else "",
                        user_agent=request.headers.get("user-agent", ""),
                        status="success" if 'response' in locals() and response.status_code < 400 else "failure"
                    )
                    db.add(log)
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                
        return response
