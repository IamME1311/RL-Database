from typing import Optional, Any

from pydantic import BaseModel

class PitchMasterRow(BaseModel):
    pitch_code: str
    year: Optional[int] = None
    org_type: str
    brand_name: str
    campaign_name: str
    requirement: str
    platform: str
    sales_lead: str
    list_lead: str
    spreadsheet_link: str


class CampaignMasterRow(BaseModel):
    campaign_code: str
    month_name: str
    year: int
    brand_name: str
    campaign_name: str
    manager: str
    member_names: list[str] = []
    spreadsheet_link: str
    report_link: str
    status: str
    expected_end_date: str
    start_date: str
    end_date: str | None = None
    report_status: str | None = None
    report_completion_date: str | None = None

    pitch_code: str


class PitchCreatorRow(BaseModel):
    source_file_id: str
    sheet: str
    platform: str
    sheet_row: str
    name: str
    profile_link: str = ""
    followers: Any = None
    category: Any = None
    tier: Any = None
    language: Any = None
    gender: Any = None
    avg_views: Any = None
    city: Any = None
    email: Any = None
    phone: Any = None
    reel_count: Any = None
    reel_story_count: Any = None
    video_story_count: Any = None
    static_carousel_count: Any = None
    event_store_visit: Any = ""
    short_form_videos_count: Any = None
    reshare_short_form_videos_count: Any = None
    dedicated_video_count: Any = None
    integrated_video_count: Any = None
    usage_rights: Any = ""
    ad_promo_rights: Any = ""
    boosting: Any = ""
    payment_terms: Any = ""
    cost_with_deliverables: Any = None
    cost_with_deliverables_usage: Any = None
    final_cost: Any = None
    brand_cost: Any = None
