from typing import Optional

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