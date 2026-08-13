from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import date

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Enum as SaEnum, ARRAY, String, Column
from pydantic import ConfigDict, HttpUrl, field_validator

from .enums import CampaignStatusChoices, MonthChoices

if TYPE_CHECKING:
    from .pitch import Pitch
    from .link_models import CampaignCreatorLink


class Campaign(SQLModel, table=True):
    model_config = ConfigDict(validate_assignment=True)

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    campaign_code: str = Field(nullable=False, unique=True, index=True)

    month_name: MonthChoices = Field(sa_type=SaEnum(MonthChoices), nullable=False)
    year: int

    brand_name: str = Field(nullable=False)
    campaign_name: str = Field(nullable=False)
    manager: str = Field(nullable=False)
    member_names: list[str] = Field(default=[], sa_column=Column(ARRAY(String)))

    pitch_id: UUID | None = Field(default=None, foreign_key=("pitch.id"))
    pitch: "Pitch" = Relationship(back_populates="campaign")

    spreadsheet_link: str = Field(sa_column=Column(String, nullable=False, unique=True))
    report_link: str = Field(sa_column=Column(String, nullable=False, unique=True))

    status: CampaignStatusChoices = Field(
        default=CampaignStatusChoices.WIP,
        sa_type=SaEnum(CampaignStatusChoices),
        nullable=False,
    )
    expected_end_date: date = Field(nullable=False)
    start_date: date = Field(nullable=False)
    end_date: Optional[date] = Field(nullable=True)

    report_status: CampaignStatusChoices = Field(
        default=CampaignStatusChoices.WIP,
        sa_type=SaEnum(CampaignStatusChoices),
        nullable=False,
    )
    report_completion_date: Optional[date] = Field(nullable=True)

    creator_data: list["CampaignCreatorLink"] = Relationship(back_populates="campaign")

    @field_validator("spreadsheet_link", "report_link", mode="before")
    @classmethod
    def _validate_and_stringify_url(cls, v: str | HttpUrl) -> str:
        # HttpUrl(...) raises pydantic.ValidationError if v isn't a valid URL
        return str(HttpUrl(v))
