from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship, Index
from sqlalchemy import CheckConstraint
from pydantic import field_validator

if TYPE_CHECKING:
    from .company import Company
    from .pitch import Pitch
    from .campaign import Campaign

GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class Brand(SQLModel, table=True):

    __table_args__ = (
        CheckConstraint(
            f"gstin = '' OR gstin ~ '{GSTIN_REGEX}'",
            name="ck_brand_gstin_format",
        ),
        Index(
            "ix_brand_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    gstin: str = Field(
        unique=True, schema_extra={"placeholder": "27AAAAA1111A1Z1"}, nullable=False
    )

    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    company: Optional["Company"] = Relationship(back_populates="brands")

    pitches: list["Pitch"] = Relationship(back_populates="brand")
    campaigns: list["Campaign"] = Relationship(back_populates="brand")

    @field_validator("name", mode="after")
    @classmethod
    def lowercase_name(cls, v: str) -> str:
        return v.lower().strip()
