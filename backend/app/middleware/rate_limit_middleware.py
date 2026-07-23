from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = {}

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        if ip not in self.rate_limits:
            self.rate_limits[ip] = []
            
        self.rate_limits[ip] = [t for t in self.rate_limits[ip] if current_time - t < 60]
        
        if len(self.rate_limits[ip]) >= 60:
            return Response("Rate limit exceeded", status_code=429, headers={"Retry-After": "60"})
            
        self.rate_limits[ip].append(current_time)
        return await call_next(request)
