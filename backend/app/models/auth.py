from typing import Optional, Annotated

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String
from pydantic import EmailStr, AfterValidator, ConfigDict

from app.core.config import settings


def is_domain_email(email: str) -> str:
    domain = email.split("@")[-1].lower().strip()
    if domain not in settings.ALLOWED_DOMAINS:
        raise ValueError(f"Domain: '{domain}' is not authorized")
    return email

WorkEmail = Annotated[EmailStr, AfterValidator(is_domain_email)]

class User(SQLModel, table=True):
    model_config = ConfigDict(validate_assignment=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(
        sa_column=Column(String, unique=True, index=True, nullable=False)
    )
    hashed_password: str = Field(nullable=False)
    is_verified: bool = Field(default=False, nullable=False)