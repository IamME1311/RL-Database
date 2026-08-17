from typing import Optional

from sqlmodel import SQLModel, Field
from pydantic import ConfigDict, field_validator


class User(SQLModel, table=True):
    model_config = ConfigDict(validate_assignment=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True, nullable=False)
    auth_provider: str = Field(default="password", nullable=False)
    hashed_password: Optional[str] = Field(default=None, nullable=True)
    is_verified: bool = Field(default=False, nullable=False)
    is_currently_employed: bool = Field(default=False, nullable=False)

    #permissions
    can_ingest: bool = Field(default=False, nullable=False)

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()
