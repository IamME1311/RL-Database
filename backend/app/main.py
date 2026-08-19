from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from redis import asyncio as redis

from app.core.config import settings
from app.core.redis_client import get_redis_pool
from app.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = get_redis_pool()
    app.state.redis = redis.Redis(connection_pool=pool)
    yield
    await app.state.redis.aclose()
    await pool.aclose()


app = FastAPI(
    lifespan=lifespan,
    title="Ripple Pulse",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS", "DELETE"],
    allow_headers=["Content-Type", "Accept", "X-CSRF-Token"],
    expose_headers=["X-Error-Code", "Retry-After"],
)


app.include_router(v1_router, prefix="/api/v1")


@app.get("/api/home")
async def home_route():
    return {"message": "Connected to RL Database backend!!"}
