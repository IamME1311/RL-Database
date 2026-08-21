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
    errors_truncated: int = 0

class IngestRowError(BaseModel):
    row: int
    field: Optional[str] = None
    message: str
    code: Optional[str] = None
    severity: str = "error"

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


##############################################################################################################################
##############################################################################################################################


# Pitch Creator


class CreatorLinkRecord(BaseModel):
    """One sheet row: a Creator plus its PitchCreatorLink."""

    source_file_id: str
    sheet_row: int
    platform: PlatformChoices
    username: str
    name: str
    followers: Optional[int] = None
    avg_views: Optional[int] = None
    tier: TierChoices = TierChoices.NA
    gender: str = ""
    city: str = ""
    categories_raw: str = ""
    languages_raw: str = ""
    email: str = ""
    phone: str = ""
    reel_count: int = 0
    reel_story_count: int = 0
    video_story_count: int = 0
    static_carousel_count: int = 0
    event_store_visit: bool = False
    short_form_videos_count: int = 0
    reshare_short_form_videos_count: int = 0
    dedicated_video_count: int = 0
    integrated_video_count: int = 0
    usage_rights: str = ""
    ad_promo_rights: str = ""
    boosting: str = ""
    payment_terms: str = ""
    reel_cost: int = 0
    reel_story_cost: int = 0
    video_story_cost: int = 0
    static_carousel_cost: int = 0
    short_form_videos_cost: int = 0
    reshare_short_form_videos_cost: int = 0
    dedicated_video_cost: int = 0
    integrated_video_cost: int = 0
    rights_cost: int = 0
    boosting_cost: int = 0
    package_cost: int = 0
    final_cost: int = 0
    brand_cost: int = 0
