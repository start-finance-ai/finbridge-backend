from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.eligibility import ConditionType, Unit
from app.schemas.program import Program


class MatchStatus(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNKNOWN = "UNKNOWN"


class UserType(str, Enum):
    PRE_FOUNDER = "PRE_FOUNDER"
    SMALL_BUSINESS_OWNER = "SMALL_BUSINESS_OWNER"
    FREELANCER = "FREELANCER"


class BusinessStatus(str, Enum):
    PRE_FOUNDER = "PRE_FOUNDER"
    REGISTERED = "REGISTERED"
    UNREGISTERED = "UNREGISTERED"
    EXISTING_BUSINESS = "EXISTING_BUSINESS"


class BusinessEntityType(str, Enum):
    CORPORATION = "CORPORATION"
    SOLE_PROPRIETOR = "SOLE_PROPRIETOR"
    SMALL_BUSINESS = "SMALL_BUSINESS"
    SME = "SME"


class Gender(str, Enum):
    FEMALE = "FEMALE"
    MALE = "MALE"


class Intent(str, Enum):
    SUPPORT_PROGRAM = "SUPPORT_PROGRAM"
    POLICY_LOAN = "POLICY_LOAN"
    FINANCIAL_RISK = "FINANCIAL_RISK"


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_type: UserType | None = None
    region: str | None = Field(default=None, min_length=1)
    business_region: str | None = Field(default=None, min_length=1)
    age: int | None = Field(default=None, ge=0, le=150)
    pre_founder: bool | None = None
    business_status: BusinessStatus | None = None
    business_age: float | None = Field(default=None, ge=0)
    business_age_unit: Unit = Unit.YEAR
    industry: str | None = Field(default=None, min_length=1)
    capital: float | None = Field(default=None, ge=0)
    intents: list[Intent] = Field(default_factory=list)
    business_entity_type: BusinessEntityType | None = None
    sales_or_income: float | None = Field(default=None, ge=0)
    employee_count: int | None = Field(default=None, ge=0)
    gender: Gender | None = None
    certifications: list[str] | None = None
    completed_education: list[str] | None = None

    @model_validator(mode="after")
    def validate_business_age_unit(self) -> "UserProfile":
        if self.business_age_unit not in {Unit.YEAR, Unit.MONTH}:
            raise ValueError("business_age_unit must be YEAR or MONTH")
        return self


class MatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    program_id: str = Field(min_length=1)
    profile: UserProfile


class ConditionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str
    condition_type: ConditionType
    source_field: str
    evidence_text: str


class ConditionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str
    condition_type: ConditionType
    status: MatchStatus
    is_exclusion: bool
    actual_value: Any | None = None
    raw_expected_value: str
    reason: str
    evidence: ConditionEvidence


class MatchEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_status: MatchStatus
    condition_results: list[ConditionResult]
    evidence: list[ConditionEvidence]
    reason: str


class SourceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    source_url: str | None
    collected_at: str | None


class MatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program: Program
    match_status: MatchStatus
    condition_results: list[ConditionResult]
    evidence: list[ConditionEvidence]
    source: SourceInfo
    reason: str
