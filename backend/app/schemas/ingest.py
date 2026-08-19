from typing import Literal, Optional
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl, field_serializer

from app.models.enums import *

class IngestSource(str, Enum):
    pitch_master = "pitch_master"
    pitch_creator = "pitch_creator"
    campaign_master = "campaign_master"
    campaign_creator = "campaign_creator"
    brands = "brands"

class IngestJobStatus(str, Enum):
    QUEUED="queued"
    RUNNING="running"
    SUCCESS="success"
    PARTIAL_SUCCESS="partial_success"
    FAILED="failed"

class IngestCounts(BaseModel):
    received: int
    inserted: int
    updated: int
    skipped: int
    failed: int

class IngestRowError(BaseModel):
    row: int
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class IngestJob(BaseModel):
    job_id: UUID
    source: IngestSource
    origin: Literal["apps_script", "upload"]
    status: IngestJobStatus
    dry_run: bool
    started_at: datetime
    finished_at: Optional[datetime] = None
    started_by: Optional[str] = None
    counts: IngestCounts
    errors: list[IngestRowError]
    message: Optional[str] = None

class IngestJobList(BaseModel):
    jobs: list[IngestJob]


class IngestSourceInfo(BaseModel):
    source: IngestSource
    label: str
    apps_script_supported: bool = False
    upload_supported: bool = False
    last_job: Optional[IngestJob] = None
    row_count: Optional[int] = None


##############################################################################################################################
##############################################################################################################################


# Pitch Master
class Pitch(BaseModel):
    pitch_code: str
    org_type: OrgTypeChoices
    brand_name: str
    brand_display_name: str
    campaign_name: str
    requirement: PitchRequirementChoices
    platform: list[PlatformChoices]
    sales_lead: str
    list_lead: str
    spreadsheet_link: HttpUrl

    @field_serializer("spreadsheet_link")
    def _ser_url(self, v: HttpUrl) -> str:
        return str(v)


##############################################################################################################################
##############################################################################################################################


# Campaign Master
class Campaign(BaseModel):
    campaign_code: str
    month_name: MonthChoices
    year: int
    brand_name: str
    brand_display_name: str
    campaign_name: str
    manager: str
    member_names: list[str]
    spreadsheet_link: HttpUrl
    report_link: HttpUrl
    status: CampaignStatusChoices
    expected_end_date: date
    start_date: date
    end_date: date | None = None
    report_status: CampaignStatusChoices
    report_completion_date: date | None = None

    pitch_code: str

    @field_serializer("spreadsheet_link", "report_link")
    def _ser_url(self, v: HttpUrl) -> str:
        return str(v)