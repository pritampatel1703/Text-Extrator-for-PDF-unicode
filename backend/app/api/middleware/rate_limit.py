"""
Rate limiting middleware using Redis sliding window.
"""

import time
from typing import Optional

import redis.asyncio as redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.exceptions import RateLimitExceededError


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based sliding window rate limiter."""

    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/api/v1/health"):
            return await call_next(request)

        # Determine rate limit based on endpoint
        path = request.url.path
        if "/upload" in path:
            limit = settings.rate_limit_upload_per_minute
        else:
            limit = settings.rate_limit_per_minute

        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}:{path.split('/')[1] if '/' in path else 'general'}"

        try:
            r = await self._get_redis()
            now = time.time()
            window = 60  # 1 minute window

            # Sliding window counter
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()

            request_count = results[2]

            if request_count > limit:
                raise RateLimitExceededError()

            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - request_count))
            response.headers["X-RateLimit-Reset"] = str(int(now + window))

            return response

        except RateLimitExceededError:
            raise
        except Exception:
            # If Redis is unavailable, allow the request
            return await call_next(request)
