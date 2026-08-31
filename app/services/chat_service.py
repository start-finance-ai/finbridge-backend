from __future__ import annotations

import html
import logging
import re
from datetime import date

from app.ai.fallback import build_template_reply
from app.ai.prompts import (
    FINBRIDGE_EXPLANATION_INSTRUCTIONS,
    build_explanation_input,
)
from app.ai.provider import AIProvider, AIProviderError, AIProviderOutputError
from app.retrieval.program_retrieval import ProgramRetrievalService
from app.retrieval.query_understanding import (
    extract_explicit_profile,
    merge_profiles,
    requests_currently_open_programs,
    requests_deadline_sort,
)
from app.schemas.chat import (
    ChatAction,
    ChatEvidence,
    ChatMatch,
    ChatMode,
    ChatProgram,
    ChatRequest,
    ChatResponse,
    ChatSource,
    ReplySource,
)
from app.schemas.eligibility import ProgramEligibility
from app.schemas.matching import (
    BusinessStatus,
    MatchResponse,
    MatchStatus,
    UserProfile,
)
from app.schemas.program import Program
from app.schemas.retrieval import ProgramSearchRequest, ProgramSearchResponse
from app.services.program_service import ProgramService
from app.utils.date_parser import calculate_application_availability, seoul_today


logger = logging.getLogger(__name__)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_LLM_PRIMARY_PROGRAM_LIMIT = 3


class ChatService:
    def __init__(
        self,
        program_service: ProgramService,
        provider: AIProvider,
        retrieval_service: ProgramRetrievalService,
    ) -> None:
        self._program_service = program_service
        self._provider = provider
        self._retrieval_service = retrieval_service

    def chat(self, request: ChatRequest) -> ChatResponse:
        today = seoul_today()
        inferred_profile = (
            extract_explicit_profile(request.message)
            if request.mode is ChatMode.GENERAL
            else None
        )
        effective_profile = merge_profiles(inferred_profile, request.focus_profile)
        raw_programs: list[Program] = []
        eligibility_by_program: dict[str, ProgramEligibility] = {}
        match_by_program: dict[str, MatchResponse] = {}
        retrieval: ProgramSearchResponse | None = None
        retrieval_attempted = False

        if request.program_id:
            program = self._program_service.get_program(request.program_id)
            raw_programs = [program]
            eligibility_by_program[program.program_id] = (
                self._program_service.get_program_eligibility(program.program_id)
            )
            if effective_profile is not None:
                match_by_program[program.program_id] = (
                    self._program_service.match_program(
                        program.program_id, effective_profile
                    )
                )
        elif (
            request.mode is ChatMode.GENERAL
            and self._retrieval_service.is_program_search_intent(request.message)
        ):
            retrieval_attempted = True
            search_request = self._search_request(request, effective_profile)
            retrieval = self._retrieval_service.search(search_request)
            for result in retrieval.results:
                program = self._program_service.get_program(
                    result.program.program_id
                )
                raw_programs.append(program)
                eligibility_by_program[program.program_id] = (
                    self._program_service.get_program_eligibility(
                        program.program_id
                    )
                )
                if effective_profile is not None:
                    match_by_program[program.program_id] = (
                        self._program_service.match_program(
                            program.program_id, effective_profile
                        )
                    )

        programs = [
            self._program_summary(program, today=today) for program in raw_programs
        ]
        matches = [
            self._chat_match(match_by_program[program.program_id])
            for program in raw_programs
            if program.program_id in match_by_program
        ]
        evidence = [
            item
            for program in raw_programs
            for item in self._evidence(
                program,
                eligibility_by_program[program.program_id],
                match_by_program.get(program.program_id),
            )
        ]
        sources = [self._source(program) for program in raw_programs]
        actions = [
            action
            for program in raw_programs
            for action in self._actions(program)
        ]
        single_match = matches[0] if request.program_id and matches else None
        match_status = single_match.match_status if single_match else None
        suggest_focus_mode = (
            request.mode is ChatMode.GENERAL and request.focus_profile is None
        )

        structured_context = {
            "mode": request.mode.value,
            "focus_profile": (
                effective_profile.model_dump(mode="json", exclude_none=True)
                if effective_profile
                else None
            ),
            "programs": [item.model_dump(mode="json") for item in programs],
            "matches": [item.model_dump(mode="json") for item in matches],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "sources": [item.model_dump(mode="json") for item in sources],
            "retrieval": (
                [
                    {
                        "program_id": result.program.program_id,
                        "retrieval_score": result.retrieval_score,
                        "matched_fields": result.matched_fields,
                    }
                    for result in retrieval.results
                ]
                if retrieval is not None
                else None
            ),
            "limitations": {
                "general_program_discovery_supported": True,
                "retrieval_method": "STRUCTURED_EXACT_KEYWORD_BASELINE",
                "retrieval_score_is_eligibility_probability": False,
                "session_persistence_supported": False,
                "structured_results_are_authoritative": True,
                "profile_source": (
                    "REQUEST_FOCUS_PROFILE"
                    if request.focus_profile is not None
                    else "MESSAGE_EXPLICIT_FIELDS"
                    if inferred_profile is not None
                    else None
                ),
            },
        }

        try:
            provider_context = self._provider_context(structured_context)
            explanation = self._provider.explain(
                instructions=FINBRIDGE_EXPLANATION_INSTRUCTIONS,
                input_text=build_explanation_input(
                    user_message=request.message,
                    structured_context=provider_context,
                ),
            )
            reply = explanation.text.strip()
            if not reply:
                raise AIProviderOutputError("AI provider returned empty output")
            reply_source = ReplySource.LLM
            model = explanation.model
        except AIProviderError as exc:
            logger.warning(
                "AI explanation fallback: error_class=%s reason=%s",
                type(exc).__name__,
                exc.reason_code,
            )
            reply = build_template_reply(
                match_status=match_status,
                has_program_context=bool(raw_programs),
                has_profile=effective_profile is not None,
                retrieval_attempted=retrieval_attempted,
                retrieval_result_count=len(raw_programs),
                structured_context=structured_context,
            )
            reply_source = ReplySource.TEMPLATE_FALLBACK
            model = None

        return ChatResponse(
            mode=request.mode,
            reply=reply,
            reply_source=reply_source,
            model=model,
            programs=programs,
            matches=matches,
            evidence=evidence,
            sources=sources,
            actions=actions,
            suggest_focus_mode=suggest_focus_mode,
            program_context_id=request.program_id,
        )

    @staticmethod
    def _search_request(
        request: ChatRequest,
        profile: UserProfile | None,
    ) -> ProgramSearchRequest:
        business_status = profile.business_status if profile else None
        if profile and business_status is None and profile.pre_founder is True:
            business_status = BusinessStatus.PRE_FOUNDER
        return ProgramSearchRequest(
            query=request.message,
            region=(profile.business_region or profile.region) if profile else None,
            business_status=business_status,
            user_type=profile.user_type if profile else None,
            industry=profile.industry if profile else None,
            profile=profile,
            open_now_only=requests_currently_open_programs(request.message),
            sort_by_deadline=requests_deadline_sort(request.message),
            limit=5,
        )

    @staticmethod
    def _program_summary(program: Program, *, today: date) -> ChatProgram:
        availability = calculate_application_availability(
            deadline_type=program.deadline_type,
            apply_start=program.apply_start,
            apply_end=program.apply_end,
            today=today,
        )
        return ChatProgram(
            program_id=program.program_id,
            program_name=program.program_name,
            provider=program.provider,
            executing_organization=program.executing_organization,
            category=program.category,
            subcategory=program.subcategory,
            target_text=program.target_type_raw,
            summary_text=program.summary_raw,
            application_method_text=program.application_method_raw,
            apply_start=program.apply_start,
            apply_end=program.apply_end,
            apply_period_text=program.apply_period_text,
            deadline_type=program.deadline_type,
            application_status=availability.status,
            application_status_note=availability.note,
            source_url=program.source_url,
        )

    @staticmethod
    def _provider_context(structured_context: dict[str, object]) -> dict[str, object]:
        programs = list(structured_context.get("programs") or [])
        primary_programs = programs[:_LLM_PRIMARY_PROGRAM_LIMIT]
        primary_ids = {item["program_id"] for item in primary_programs}

        compact_programs = []
        for item in primary_programs:
            compact = dict(item)
            compact["target_text"] = _compact_context_text(item.get("target_text"), 300)
            compact["summary_text"] = _compact_context_text(item.get("summary_text"), 600)
            compact["application_method_text"] = _compact_context_text(
                item.get("application_method_text"), 300
            )
            compact_programs.append(compact)

        provider_context = dict(structured_context)
        provider_context["programs"] = compact_programs
        for key in ("matches", "evidence", "sources", "retrieval"):
            items = structured_context.get(key)
            if isinstance(items, list):
                provider_context[key] = [
                    item
                    for item in items
                    if item.get("program_id") in primary_ids
                ]
        provider_context["additional_candidates"] = [
            {
                "program_id": item["program_id"],
                "program_name": item["program_name"],
                "application_status": item["application_status"],
                "source_url": item.get("source_url"),
            }
            for item in programs[_LLM_PRIMARY_PROGRAM_LIMIT:]
        ]
        provider_context["reply_policy"] = {
            "detailed_program_limit": _LLM_PRIMARY_PROGRAM_LIMIT,
            "structured_program_count": len(programs),
        }
        return provider_context

    @staticmethod
    def _chat_match(match: MatchResponse) -> ChatMatch:
        return ChatMatch(
            program_id=match.program.program_id,
            match_status=match.match_status,
            condition_results=match.condition_results,
            reason=match.reason,
        )

    @staticmethod
    def _evidence(
        program: Program | None,
        eligibility: ProgramEligibility | None,
        match: MatchResponse | None,
    ) -> list[ChatEvidence]:
        if program is None or eligibility is None:
            return []
        if match is not None:
            raw_evidence = match.evidence
        else:
            conditions = [
                *eligibility.common_conditions,
                *(
                    condition
                    for group in eligibility.eligibility_groups
                    for condition in group.conditions
                ),
                *eligibility.global_exclusions,
            ]
            raw_evidence = conditions

        return [
            ChatEvidence(
                program_id=program.program_id,
                condition_id=item.condition_id,
                condition_type=item.condition_type,
                source_field=item.source_field,
                evidence_text=item.evidence_text,
            )
            for item in raw_evidence
        ]

    @staticmethod
    def _source(program: Program) -> ChatSource:
        return ChatSource(
            program_id=program.program_id,
            source=program.source,
            source_url=program.source_url,
        )

    @staticmethod
    def _actions(program: Program | None) -> list[ChatAction]:
        if program is None:
            return []
        actions = [
            ChatAction(
                action_type="VIEW_PROGRAM_DETAIL",
                label="지원사업 상세 보기",
                program_id=program.program_id,
                href=f"/programs/{program.program_id}",
            )
        ]
        if program.source_url:
            actions.append(
                ChatAction(
                    action_type="VIEW_OFFICIAL_SOURCE",
                    label="공식 공고 확인",
                    program_id=program.program_id,
                    href=str(program.source_url),
                )
            )
        return actions


def _compact_context_text(value: object, limit: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    plain = html.unescape(_HTML_TAG_RE.sub(" ", value))
    plain = _WHITESPACE_RE.sub(" ", plain).strip()
    if len(plain) <= limit:
        return plain
    boundary = max(
        plain.rfind(". ", 0, limit),
        plain.rfind("다. ", 0, limit),
        plain.rfind("요. ", 0, limit),
    )
    if boundary >= limit // 2:
        return plain[: boundary + 1]
    return plain[:limit].rstrip() + " …(원문 일부)"
