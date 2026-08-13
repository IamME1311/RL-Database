from enum import Enum
import json

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.services.apps_script_client import Client
from app.services.ingest import Ingest

router = APIRouter()

ingest_service = Ingest()

class IngestType(str, Enum):
    pitch_master = "pitch_master"
    pitch_creator = "pitch_creator"
    campaign_master = "campaign_master"
    campaign_creator = "campaign_creator"


@router.get("/ingest_json/{type}")
async def ingest_json(session: SessionDep, ingest_type: IngestType):
    client = Client()

    response = {
        "status" : "Failed",
        "message" : "Something went wrong"
    }

    if ingest_type == IngestType.pitch_master:
        api_response = await client.fetch_pitch_master_data()

        if api_response["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=api_response["message"],
            )

        data = api_response.get("data")
        response = await ingest_service.ingest_pitch_master_data(session, data)

    elif ingest_type ==IngestType.campaign_master:
        api_response = await client.fetch_campaign_master_data()

        if api_response["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=api_response["message"],
            )

        data = api_response.get("data")
        response = await ingest_service.ingest_campaign_master_data(session, data)

    return response
