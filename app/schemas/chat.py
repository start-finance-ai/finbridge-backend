from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.schemas.eligibility import ConditionType
from app.schemas.matching import (
    ConditionResult,
    MatchStatus,
    UserProfile,
)
from app.utils.date_parser import DeadlineType


class ChatMode(str, Enum):
    GENERAL = "GENERAL"
    FOCUS = "FOCUS"


class ReplySource(str, Enum):
    LLM = "LLM"
    TEMPLATE_FALLBACK = "TEMPLATE_FALLBACK"


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: ChatMode = ChatMode.GENERAL
    message: str = Field(min_length=1, max_length=4000)
    focus_profile: UserProfile | None = None
    program_id: str | None = Field(default=None, min_length=1, max_length=100)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)


class ChatProgram(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    program_name: str
    provider: str | None
    executing_organization: str | None
    category: str | None
    subcategory: str | None
    target_text: str | None
    summary_text: str | None
    application_method_text: str | None
    apply_start: date | None
    apply_end: date | None
    apply_period_text: str | None
    deadline_type: DeadlineType
    source_url: AnyHttpUrl | None


class ChatMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    match_status: MatchStatus
    condition_results: list[ConditionResult]
    reason: str


class ChatEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    condition_id: str
    condition_type: ConditionType
    source_field: str
    evidence_text: str


class ChatSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: str
    source: str
    source_url: AnyHttpUrl | None


class ChatAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str
    label: str
    program_id: str | None = None
    href: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ChatMode
    reply: str
    reply_source: ReplySource
    model: str | None
    programs: list[ChatProgram]
    matches: list[ChatMatch]
    evidence: list[ChatEvidence]
    sources: list[ChatSource]
    actions: list[ChatAction]
    suggest_focus_mode: bool
    program_context_id: str | None
