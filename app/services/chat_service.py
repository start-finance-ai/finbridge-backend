from __future__ import annotations

from app.ai.fallback import build_template_reply
from app.ai.prompts import (
    FINBRIDGE_EXPLANATION_INSTRUCTIONS,
    build_explanation_input,
)
from app.ai.provider import AIProvider, AIProviderError, AIProviderOutputError
from app.schemas.chat import (
    ChatAction,
    ChatEvidence,
    ChatMatch,
    ChatProgram,
    ChatRequest,
    ChatResponse,
    ChatSource,
    ReplySource,
)
from app.schemas.eligibility import ProgramEligibility
from app.schemas.matching import MatchResponse, MatchStatus
from app.schemas.program import Program
from app.services.program_service import ProgramService


class ChatService:
    def __init__(self, program_service: ProgramService, provider: AIProvider) -> None:
        self._program_service = program_service
        self._provider = provider

    def chat(self, request: ChatRequest) -> ChatResponse:
        program: Program | None = None
        eligibility: ProgramEligibility | None = None
        match: MatchResponse | None = None

        if request.program_id:
            program = self._program_service.get_program(request.program_id)
            eligibility = self._program_service.get_program_eligibility(
                request.program_id
            )
            if request.focus_profile is not None:
                match = self._program_service.match_program(
                    request.program_id, request.focus_profile
                )

        programs = [self._program_summary(program)] if program else []
        matches = [self._chat_match(match)] if match else []
        evidence = self._evidence(program, eligibility, match)
        sources = [self._source(program)] if program else []
        actions = self._actions(program)
        match_status = match.match_status if match else None
        suggest_focus_mode = (
            request.mode.value == "GENERAL" and request.focus_profile is None
        )

        structured_context = {
            "mode": request.mode.value,
            "focus_profile": (
                request.focus_profile.model_dump(mode="json", exclude_none=True)
                if request.focus_profile
                else None
            ),
            "programs": [item.model_dump(mode="json") for item in programs],
            "matches": [item.model_dump(mode="json") for item in matches],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "sources": [item.model_dump(mode="json") for item in sources],
            "limitations": {
                "general_program_discovery_supported": False,
                "session_persistence_supported": False,
                "structured_results_are_authoritative": True,
            },
        }

        try:
            explanation = self._provider.explain(
                instructions=FINBRIDGE_EXPLANATION_INSTRUCTIONS,
                input_text=build_explanation_input(
                    user_message=request.message,
                    structured_context=structured_context,
                ),
            )
            reply = explanation.text.strip()
            if not reply:
                raise AIProviderOutputError("AI provider returned empty output")
            reply_source = ReplySource.LLM
            model = explanation.model
        except AIProviderError:
            reply = build_template_reply(
                match_status=match_status,
                has_program_context=program is not None,
                has_profile=request.focus_profile is not None,
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
            program_context_id=program.program_id if program else None,
        )

    @staticmethod
    def _program_summary(program: Program) -> ChatProgram:
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
            source_url=program.source_url,
        )

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
