"""Raw ingest rows -> validated intermediate models.

Every row is parsed independently: a bad row yiels an IngestRowError and
is skipped rather than aborting the batch. Enum coercion is total -- an unknown
value maps to the NA member instead of raising.
"""

from typing import NamedTuple, Any, Optional
from datetime import date, datetime
import re

from pydantic import ValidationError

from app.schemas.apps_script_response import PitchMasterRow, CampaignMasterRow
from app.schemas.ingest import Pitch, Campaign, IngestRowError
from app.models.enums import (
    OrgTypeChoices,
    PitchRequirementChoices,
    PlatformChoices,
    CampaignStatusChoices,
    MonthChoices,
)

_YEAR_SUFFIX = re.compile(r"-\d{4}$")

_ORG_TYPE = {
    "brand - core": OrgTypeChoices.BRAND_CORE,
    "brand-core": OrgTypeChoices.BRAND_CORE,
    "brand - other": OrgTypeChoices.BRAND_OTHER,
    "brand-other": OrgTypeChoices.BRAND_OTHER,
    "agency": OrgTypeChoices.AGENCY,
    "retainer account": OrgTypeChoices.RETAINER_ACC,
    "retainer_account": OrgTypeChoices.RETAINER_ACC,
}

_REQUIREMENT = {
    "list": PitchRequirementChoices.LIST,
    "plan": PitchRequirementChoices.PLAN,
    "list and plan": PitchRequirementChoices.LIST_AND_PLAN,
    "content buckets": PitchRequirementChoices.CONTENT_BUCKETS,
    "media plan": PitchRequirementChoices.MEDIA_PLAN,
    "production": PitchRequirementChoices.PRODUCTION,
    "content buckets and list": PitchRequirementChoices.CONTENT_BUCKETS_AND_LIST,
    "demographics/data": PitchRequirementChoices.DEMOGRAPHICS_DATA,
}

_PLATFORM = {
    "instagram": [PlatformChoices.INSTAGRAM],
    "insta": [PlatformChoices.INSTAGRAM],
    "ig": [PlatformChoices.INSTAGRAM],
    "yt": [PlatformChoices.YOUTUBE],
    "youtube": [PlatformChoices.YOUTUBE],
    "linkedin": [PlatformChoices.LINKEDIN],
    "facebook": [PlatformChoices.FACEBOOK],
    "others": [PlatformChoices.OTHERS],
    "insta + yt": [PlatformChoices.INSTAGRAM, PlatformChoices.YOUTUBE],
    "insta + others": [PlatformChoices.INSTAGRAM, PlatformChoices.OTHERS],
    "yt & linkedin": [PlatformChoices.YOUTUBE, PlatformChoices.LINKEDIN],
    "ig & linkedin": [PlatformChoices.INSTAGRAM, PlatformChoices.LINKEDIN],
}

_DATE_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y")


class ParseOutcome(NamedTuple):
    rows: list[Pitch] | list[Campaign]
    errors: list[IngestRowError]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _key(value: Any) -> str:
    return _clean(value).lower()


def normalize_brand_name(raw: Any) -> str:
    return _key(raw)


def _pitch_code(raw: Any, year: Optional[int]) -> str:
    code = _clean(raw).upper()
    if not code:
        raise ValueError("pitch_code: missing")
    if not _YEAR_SUFFIX.search(code):
        raise ValueError(f"pitch_code: expected a -YYYY suffix, got {code!r}")
    return f"{code}-{year or date.today().year}"


def _parse_date(value: Any, field: str) -> Optional[date]:
    text = _clean(value)
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        raise ValueError(f"{field}: unrecognized date {text!r}")


class Parser:

    async def parse_pitch_master(self, raw_data: list[dict]) -> ParseOutcome:
        rows, errors = [], []
        for i, raw in enumerate(raw_data):
            try:
                r = PitchMasterRow.model_validate(raw)
                rows.append(
                    Pitch(
                        pitch_code=_pitch_code(r.pitch_code, r.year),
                        org_type=_ORG_TYPE.get(_key(r.org_type), OrgTypeChoices.NA),
                        brand_name=normalize_brand_name(r.brand_name),
                        brand_display_name=_clean(r.brand_name),
                        campaign_name=_clean(r.campaign_name),
                        requirement=_REQUIREMENT.get(
                            _key(r.requirement), PitchRequirementChoices.NA
                        ),
                        platform=_PLATFORM.get(_key(r.platform), [PlatformChoices.NA]),
                        sales_lead=_clean(r.sales_lead),
                        list_lead=_clean(r.list_lead),
                        spreadsheet_link=str(r.spreadsheet_link),
                    )
                )
            except (ValidationError, ValueError) as e:
                errors.append(IngestRowError(row=i, message=str(e)))
        return ParseOutcome(rows, errors)

    async def parse_campaign_master(self, raw_data: list[dict]) -> ParseOutcome:
        rows, errors = [], []
        for i, raw in enumerate(raw_data):
            try:
                r = CampaignMasterRow.model_validate(raw)

                status = (
                    CampaignStatusChoices(_key(r.status))
                    if _key(r.status)
                    else CampaignStatusChoices.WIP
                )
                if _clean(r.report_status):
                    report_status = CampaignStatusChoices(_key(r.report_status))
                elif status == CampaignStatusChoices.SCRAPPED:
                    report_status = status
                else:
                    report_status = CampaignStatusChoices.WIP

                rows.append(
                    Campaign(
                        campaign_code=_clean(r.campaign_code).upper(),
                        month_name=MonthChoices(_key(r.month_name)),
                        year=r.year,
                        brand_name=normalize_brand_name(r.brand_name),
                        brand_display_name=_clean(r.brand_name),
                        campaign_name=_clean(r.campaign_name),
                        manager=_clean(r.manager),
                        member_names=[
                            _clean(m) for m in (r.member_names or []) if _clean(m)
                        ],
                        spreadsheet_link=str(r.spreadsheet_link),
                        report_link=str(r.report_link),
                        status=status,
                        expected_end_date=_parse_date(
                            r.expected_end_date, "expected_end_date"
                        ),
                        start_date=_parse_date(r.start_date, "start_date"),
                        end_date=_parse_date(r.end_date, "end_date"),
                        report_status=report_status,
                        report_completion_date=_parse_date(
                            r.report_completion_date, "report_completion_date"
                        ),
                        pitch_code=_pitch_code(r.pitch_code, r.year),
                    )
                )
            except (ValidationError, ValueError) as e:
                errors.append(IngestRowError(row=i, message=str(e)))
        return ParseOutcome(rows, errors)
