"""Redis-based sliding window rate limiter."""

import time
import uuid

from redis.asyncio import Redis

from app.core.exceptions import RateLimitError


class RateLimiter:
    """Sliding window rate limiter using Redis sorted sets.

    Implementation notes:
      - We first count current requests in the window. If the bucket is full,
        we refuse WITHOUT adding the request — otherwise denied requests would
        keep extending the bucket forever and rate-limited clients would never
        recover.
      - Each entry's value is `{timestamp}:{uuid4}` so two requests in the
        same microsecond don't collide on the sorted-set member key.
      - All ops happen in a Redis pipeline for one round-trip.
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> dict[str, int]:
        """
        Atomically test-and-add a request to the sliding window bucket.

        Returns rate-limit info on success.
        Raises RateLimitError when the bucket is full (without adding the
        denied request to the bucket).
        """
        now = time.time()
        window_start = now - window_seconds

        # Step 1: prune + count without modifying.
        prune_pipe = self.redis.pipeline()
        prune_pipe.zremrangebyscore(key, 0, window_start)
        prune_pipe.zcard(key)
        prune_results = await prune_pipe.execute()
        existing = prune_results[1]

        if existing >= limit:
            # Bucket full — don't add, and surface info via the exception.
            raise RateLimitError(
                f"Rate limit exceeded: {existing}/{limit} requests in {window_seconds}s"
            )

        # Step 2: register this request.
        member = f"{now}:{uuid.uuid4().hex}"
        add_pipe = self.redis.pipeline()
        add_pipe.zadd(key, {member: now})
        add_pipe.expire(key, window_seconds)
        await add_pipe.execute()

        new_count = existing + 1
        return {
            "limit": limit,
            "remaining": max(0, limit - new_count),
            "reset": int(now + window_seconds),
        }
