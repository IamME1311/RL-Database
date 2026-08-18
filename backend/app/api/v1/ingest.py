from enum import Enum
import json

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep, CurrentUser
from app.services.ingest import Ingest
from app.schemas.ingest import IngestSourceInfo, IngestSource

router = APIRouter()

ingest_service = Ingest()


class IngestType(str, Enum):
    pitch_master = "pitch_master"
    pitch_creator = "pitch_creator"
    campaign_master = "campaign_master"
    campaign_creator = "campaign_creator"
    brands = "brands"


@router.get("/sources")
async def ingest_sources(user: CurrentUser):
    sources_data = [
        IngestSourceInfo(
            source=IngestSource.pitch_master,
            label="Pitch Master",
            apps_script_supported=False,
            upload_supported=True,
        ),
        IngestSourceInfo(
            source=IngestSource.campaign_master,
            label="Campaign Master",
            apps_script_supported=False,
            upload_supported=True,
        ),
        IngestSourceInfo(
            source=IngestSource.pitch_creator,
            label="Pitch Creator",
            apps_script_supported=False,
            upload_supported=True,
        ),
        IngestSourceInfo(
            source=IngestSource.campaign_creator,
            label="Campaign Creator",
            apps_script_supported=False,
            upload_supported=True,
        ),
        IngestSourceInfo(
            source=IngestSource.brands,
            label="Brands",
            apps_script_supported=False,
            upload_supported=True,
        )
    ]

    return {"sources": sources_data}
