from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB


class IngestJob(SQLModel, table=True):
    __tablename__ = "ingest_job"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: UUID = Field(default_factory=uuid4, unique=True, index=True)
    source: str = Field(nullable=False, index=True)
    origin: str = Field(nullable=False)
    status: str = Field(nullable=False, index=True)
    dry_run: bool = Field(default=False, nullable=False)
    file_name: Optional[str] = Field(default=None)

    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    finished_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    started_by: Optional[str] = Field(nullable=True)

    received: int = Field(default=0, nullable=False)
    inserted: int = Field(default=0, nullable=False)
    updated: int = Field(default=0, nullable=False)
    skipped: int = Field(default=0, nullable=False)
    failed: int = Field(default=0, nullable=False)

    errors: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    errors_truncated: int = Field(default=0, nullable=False)
    message: Optional[str] = Field(default=None)
