from fastapi import APIRouter

from .health import router as health_router
from .ingest import router as ingest_router

router = APIRouter()

router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
