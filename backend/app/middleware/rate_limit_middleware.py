from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import time
from app.core.config import get_settings

settings = get_settings()

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = {}
        self.last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        # Check reverse proxy headers in priority order
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in list is the original client
            return forwarded.split(",")[0].strip()
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "127.0.0.1"

    async def dispatch(self, request: Request, call_next):
        # Exempt health check and assets
        if request.url.path == "/health" or request.url.path.startswith("/assets/"):
            return await call_next(request)

        ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Periodic cleanup of expired entries every 5 minutes to prevent unbounded memory growth
        if current_time - self.last_cleanup > 300:
            self.rate_limits = {
                k: [t for t in v if current_time - t < 60]
                for k, v in self.rate_limits.items()
                if any(current_time - t < 60 for t in v)
            }
            self.last_cleanup = current_time

        if ip not in self.rate_limits:
            self.rate_limits[ip] = []
            
        self.rate_limits[ip] = [t for t in self.rate_limits[ip] if current_time - t < 60]
        
        limit = settings.RATE_LIMIT_PER_MINUTE or 60
        if len(self.rate_limits[ip]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before making more requests."},
                headers={"Retry-After": "60"}
            )
            
        self.rate_limits[ip].append(current_time)
        return await call_next(request)
