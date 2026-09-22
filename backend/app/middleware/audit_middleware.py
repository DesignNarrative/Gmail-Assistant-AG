from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.database import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.core.security import decode_token
import logging
import uuid

logger = logging.getLogger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health") or request.url.path.startswith("/assets/"):
            return await call_next(request)
            
        # Extract user_id from Authorization header if present
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            payload = decode_token(token)
            if payload and "sub" in payload:
                try:
                    user_id = uuid.UUID(payload["sub"])
                except Exception:
                    pass

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
        finally:
            try:
                # Determine client IP with proxy support
                client_ip = (
                    request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                    or request.headers.get("cf-connecting-ip")
                    or request.headers.get("x-real-ip")
                    or (request.client.host if request.client else "")
                )
                async with AsyncSessionLocal() as db:
                    log = AuditLog(
                        user_id=user_id,
                        action=f"{request.method} {request.url.path}",
                        ip_address=client_ip,
                        user_agent=request.headers.get("user-agent", "")[:255],
                        status="success" if 'response' in locals() and response.status_code < 400 else "failure"
                    )
                    db.add(log)
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                
        return response
