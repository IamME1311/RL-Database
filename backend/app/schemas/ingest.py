from datetime import date

from pydantic import BaseModel, HttpUrl

from app.models.enums import *

# Pitch Master
class Pitch(BaseModel):
    pitch_code: str
    org_type: OrgTypeChoices
    company_name: str
    campaign_name: str
    requirement: PitchRequirementChoices
    platform: list[PlatformChoices]
    sales_lead: str
    list_lead: str
    spreadsheet_link: HttpUrl


##############################################################################################################################
##############################################################################################################################


# Campaign Master
class Campaign(BaseModel):
    campaign_code: str
    month_name: MonthChoices
    year: int
    brand_name: str
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
