from uuid import uuid4, UUID
from typing import Optional, TYPE_CHECKING, Annotated

from sqlmodel import SQLModel, Field, Relationship, String
from sqlalchemy import Enum as SaEnum, Column
from sqlalchemy.dialects.postgresql import ARRAY
from pydantic import ConfigDict
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

from .link_models import CategoryCreatorLink, LanguageCreatorLink
from .enums import PlatformChoices, TierChoices

if TYPE_CHECKING:
    # This runs ONLY during static analysis/IDE linting.
    # Python completely ignores this block at runtime, breaking the circular import.
    from .category import Category
    from .language import Language
    from .link_models import PitchCreatorLink, CampaignCreatorLink


IndianPhoneNumber = Annotated[
    str,
    PhoneNumberValidator(
        default_region="IN", number_format="E164", supported_regions=["IN"]
    ),
]


class Creator(SQLModel, table=True):
    model_config = ConfigDict(validate_assignment=True)

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    platform: PlatformChoices = Field(sa_type=SaEnum(PlatformChoices))
    username: str = Field(default=None, unique=True, nullable=False)

    name: str
    followers: int = Field(nullable=True)
    tier: TierChoices = Field(sa_type=SaEnum(TierChoices))
    avg_views: int = Field(nullable=True)

    # CATEGORIES
    categories: list["Category"] = Relationship(
        back_populates="creators", link_model=CategoryCreatorLink
    )
    categories_raw: str

    # LANGUAGES
    languages: list["Language"] = Relationship(
        back_populates="creators", link_model=LanguageCreatorLink
    )
    languages_raw: str

    gender: str
    city: str

    email: str = Field(sa_column=Column(String, nullable=True))
    phone: str = Field(sa_column=Column(String, nullable=True))

    additional_emails: list[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    additional_phones: list[int] = Field(default=[], sa_column=Column(ARRAY(String)))

    affiliated_pitches: list["PitchCreatorLink"] = Relationship(
        back_populates="creator",
    )
    affiliated_campaigns: list["CampaignCreatorLink"] = Relationship(
            back_populates="creator",
        )
