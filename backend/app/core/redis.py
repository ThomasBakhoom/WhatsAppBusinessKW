from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings

settings = get_settings()

pool = ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
    decode_responses=True,
)


async def get_redis() -> Redis:
    """Get an async Redis client from the connection pool."""
    return Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    await pool.disconnect()
