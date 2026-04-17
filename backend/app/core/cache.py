"""Redis caching layer for hot data."""

import json
from typing import Any

import structlog

from app.core.redis import get_redis

logger = structlog.get_logger()

DEFAULT_TTL = 300  # 5 minutes


async def cache_get(key: str) -> Any | None:
    """Get a value from cache."""
    try:
        redis = await get_redis()
        data = await redis.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Set a value in cache with TTL."""
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    """Delete a cache key."""
    try:
        redis = await get_redis()
        await redis.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern."""
    try:
        redis = await get_redis()
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass


def company_key(company_id: str, resource: str, resource_id: str = "") -> str:
    """Build a namespaced cache key."""
    if resource_id:
        return f"co:{company_id}:{resource}:{resource_id}"
    return f"co:{company_id}:{resource}"
