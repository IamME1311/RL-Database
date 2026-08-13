from fastapi import APIRouter, HTTPException, status
from sqlmodel import text

from app.api.deps import RedisDep, SessionDep

router = APIRouter()


@router.get("/redis")
async def redis_health(r: RedisDep):
    try:
        pong = await r.ping()
        return {"service": "redis", "status": "up" if pong else "down"}
    except Exception as e:
        print(f"Redis health check failed! : {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="redis is down!",
        )


@router.get("/postgresdb")
async def db_health(session: SessionDep):
    try:
        result = await session.exec(text("SELECT 1"))
        result.first()

        return {
            "service": "postgres",
            "status": "up",
        }
    except Exception as e:
        print(f"Database health check failed! : {e}")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="databse connection failed!",
        )
