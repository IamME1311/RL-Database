from redis import asyncio as redis

from app.core.config import settings

redis_pool: redis.ConnectionPool | None = None

def get_redis_pool() -> redis.ConnectionPool:
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            str(settings.REDIS_URL),
            max_connections=20,
            decode_responses=True
        )
    return redis_pool


async def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=get_redis_pool())