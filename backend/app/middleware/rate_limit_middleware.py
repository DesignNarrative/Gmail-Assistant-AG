from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from redis import asyncio as aioredis
from app.core.config import get_settings
import logging
import time
import uuid

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter.

    Primary backend is Redis (a sorted set per IP), so the limit is shared across
    multiple workers/processes. If Redis is unreachable it degrades gracefully to a
    per-process in-memory window so the app keeps serving (single-process mode never
    needs Redis for this, but production multi-worker does).
    """

    def __init__(self, app):
        super().__init__(app)
        self.limit = settings.RATE_LIMIT_PER_MINUTE
        self.window = 60  # seconds
        # On Windows, 'localhost' resolves to IPv6 (::1) first and redis.asyncio stalls
        # ~2s before falling back to IPv4 where Redis actually listens. Force IPv4.
        redis_url = settings.REDIS_URL.replace("//localhost:", "//127.0.0.1:")
        try:
            self.redis = aioredis.from_url(
                redis_url, socket_connect_timeout=2, socket_timeout=2
            )
        except Exception as e:
            logger.warning(f"Rate limiter could not init Redis client, using in-memory fallback: {e}")
            self.redis = None
        # In-memory fallback store: {ip: [timestamps]}
        self._memory = {}

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.time()

        if await self._is_rate_limited(ip, now):
            return Response(
                "Rate limit exceeded", status_code=429, headers={"Retry-After": str(self.window)}
            )
        return await call_next(request)

    async def _is_rate_limited(self, ip: str, now: float) -> bool:
        # Try Redis-backed sliding window first.
        if self.redis is not None:
            try:
                key = f"ratelimit:{ip}"
                cutoff = now - self.window
                member = f"{now}:{uuid.uuid4().hex}"
                pipe = self.redis.pipeline()
                pipe.zremrangebyscore(key, 0, cutoff)  # drop entries outside the window
                pipe.zadd(key, {member: now})          # record this request
                pipe.zcard(key)                        # count requests in the window
                pipe.expire(key, self.window)          # auto-clean idle IPs
                results = await pipe.execute()
                count = results[2]
                return count > self.limit
            except Exception as e:
                # Redis blip: log once-ish and fall through to in-memory this request.
                logger.warning(f"Rate limiter Redis error, falling back to in-memory: {e}")

        # In-memory fallback (per-process).
        timestamps = self._memory.get(ip, [])
        timestamps = [t for t in timestamps if now - t < self.window]
        if len(timestamps) >= self.limit:
            self._memory[ip] = timestamps
            return True
        timestamps.append(now)
        self._memory[ip] = timestamps
        return False
