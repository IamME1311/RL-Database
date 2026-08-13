from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from redis import asyncio as redis

from app.core.db import get_session
from app.core.redis_client import get_redis

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[redis.Redis, Depends(get_redis)]