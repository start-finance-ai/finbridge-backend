from __future__ import annotations

from datetime import date

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.schemas.matching import BusinessStatus, UserType
from app.utils.date_parser import DeadlineType


class ProgramSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str | None = Field(default=None, min_length=1, max_length=500)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    business_status: BusinessStatus | None = None
    user_type: UserType | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = Field(default=None, min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=20)


class ProgramSearchProgram(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    program_name: str
    provider: str | None
    executing_organization: str | None
    category: str | None
    subcategory: str | None
    target_text: str | None
    summary_text: str | None
    apply_start: date | None
    apply_end: date | None
    apply_period_text: str | None
    deadline_type: DeadlineType


class ProgramSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program: ProgramSearchProgram
    retrieval_score: int = Field(ge=0)
    matched_fields: list[str]
    source: str
    source_url: AnyHttpUrl | None


class ProgramSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[ProgramSearchResult]
    result_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=20)
    score_semantics: str = "DETERMINISTIC_RANKING_ONLY"
