from datetime import date, datetime

from app.schemas.apps_script_response import PitchMasterRow, CampaignMasterRow
from app.schemas.ingest import Pitch, Campaign
from app.models.enums import *


class Parser:

    async def parse_pitch_master(self, raw_data: list[PitchMasterRow]) -> list[Pitch]:
        clean_data = list()
        for raw in raw_data:
            r = PitchMasterRow.model_validate(raw)

            pitch_code = f"{r.pitch_code}-{date.today().year}"

            # fix org type
            org_type_raw = r.org_type.lower().strip()
            org_type = {
                "brand - core": OrgTypeChoices.BRAND_CORE,
                "brand - other": OrgTypeChoices.BRAND_OTHER,
                "agency": OrgTypeChoices.AGENCY,
                "retainer account": OrgTypeChoices.RETAINER_ACC,
            }.get(org_type_raw, OrgTypeChoices.NA)

            # fix requirement
            requirement_raw = r.requirement.lower().strip()
            requirement = {
                "list": PitchRequirementChoices.LIST,
                "plan": PitchRequirementChoices.PLAN,
                "list and plan": PitchRequirementChoices.LIST_AND_PLAN,
                "content buckets": PitchRequirementChoices.CONTENT_BUCKETS,
                "media plan": PitchRequirementChoices.MEDIA_PLAN,
                "production": PitchRequirementChoices.PRODUCTION,
                "content buckets and list": PitchRequirementChoices.CONTENT_BUCKETS_AND_LIST,
                "demographics/data": PitchRequirementChoices.DEMOGRAPHICS_DATA,
            }.get(requirement_raw, PitchRequirementChoices.NA)

            # fix platform
            platform_raw = r.platform.lower().strip()
            platform = {
                "instagram": [PlatformChoices.INSTAGRAM],
                "yt": [PlatformChoices.YOUTUBE],
                "insta + yt": [PlatformChoices.INSTAGRAM, PlatformChoices.YOUTUBE],
                "others": [PlatformChoices.OTHERS],
                "insta + others": [PlatformChoices.INSTAGRAM, PlatformChoices.OTHERS],
                "linkedin": [PlatformChoices.LINKEDIN],
                "yt & linkedin": [PlatformChoices.YOUTUBE, PlatformChoices.LINKEDIN],
                "ig & linkedin": [PlatformChoices.INSTAGRAM, PlatformChoices.LINKEDIN],
            }.get(platform_raw, [PlatformChoices.NA])

            clean_data.append(
                Pitch(
                    pitch_code=pitch_code,
                    org_type=org_type,
                    company_name=r.company_name,
                    campaign_name=r.campaign_name,
                    requirement=requirement,
                    platform=platform,
                    sales_lead=r.sales_lead,
                    list_lead=r.list_lead,
                    spreadsheet_link=r.spreadsheet_link,
                )
            )

        return clean_data

    async def parse_campaign_master(
        self, raw_data: list[CampaignMasterRow]
    ) -> list[Campaign]:
        clean_data = list()

        for raw in raw_data:
            r = CampaignMasterRow.model_validate(raw)

            pitch_code = f"{r.pitch_code.strip().upper()}-{date.today().year}"
            month_name = r.month_name.lower().strip()
            brand_name = r.brand_name.lower().strip()
            campaign_name = r.campaign_name.lower().strip()
            manager = r.manager.lower().strip()
            status = r.status.lower().strip()

            if r.report_status:
                report_status = r.report_status.lower().strip()
            else:
                report_status = CampaignStatusChoices.WIP

            expected_end_date = datetime.fromisoformat(r.expected_end_date).date()
            start_date = datetime.fromisoformat(r.start_date).date()

            if r.end_date:
                end_date = datetime.fromisoformat(r.end_date).date()
            else:
                end_date = None

            if r.report_completion_date:
                report_completion_date = datetime.fromisoformat(r.report_completion_date).date()
            else:
                report_completion_date = None


            clean_data.append(Campaign(
                campaign_code=r.campaign_code,
                month_name=month_name,
                year=r.year,
                brand_name=brand_name,
                campaign_name=campaign_name,
                manager=manager,
                member_names=r.member_names,
                spreadsheet_link=r.spreadsheet_link,
                report_link=r.report_link,
                status=status,
                expected_end_date=expected_end_date,
                start_date=start_date,
                end_date=end_date,
                report_status=report_status,
                report_completion_date=report_completion_date,
                pitch_code=pitch_code
            ))

        return clean_data
