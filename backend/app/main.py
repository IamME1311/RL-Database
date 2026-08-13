from fastapi import FastAPI
from contextlib import asynccontextmanager
from redis import asyncio as redis

from app.core.db import init_db
from app.core.redis_client import get_redis_pool
# from app.api.deps import RedisDep
from app.api.v1 import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # await init_db(reset=True) # for DEV only
    pool = get_redis_pool()
    app.state.redis = redis.Redis(connection_pool=pool)
    yield
    await app.state.redis.aclose()
    await pool.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def home_route():
    return {"message": "Connected to RL Database backend!!"}
