from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.utils.date_parser import DeadlineType


class Program(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    program_id: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    provider: str | None = None
    executing_organization: str | None = None
    category: str | None = None
    subcategory: str | None = None
    target_type_raw: str | None = None
    hashtags_raw: str | None = None
    summary_raw: str | None = None
    application_method_raw: str | None = None
    contact_raw: str | None = None
    apply_start: date | None = None
    apply_end: date | None = None
    apply_period_text: str | None = None
    deadline_type: DeadlineType
    source: str = "BIZINFO"
    source_url: AnyHttpUrl | None = None
    document_url: AnyHttpUrl | None = None
    document_name: str | None = None
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None
    collected_at: datetime | None = None
    raw_source: dict[str, Any]
