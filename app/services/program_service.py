from __future__ import annotations

from app.data.program_repository import ProgramRepository
from app.eligibility.extractor import EligibilityExtractor
from app.eligibility.matcher import EligibilityMatcher
from app.schemas.eligibility import ProgramEligibility, ProgramExtractionStatus
from app.schemas.matching import MatchResponse, SourceInfo, UserProfile
from app.schemas.program import Program


class ProgramNotFoundError(LookupError):
    pass


class ProgramService:
    def __init__(
        self,
        repository: ProgramRepository,
        matcher: EligibilityMatcher | None = None,
        extractor: EligibilityExtractor | None = None,
        eligibility_by_program_id: dict[str, ProgramEligibility] | None = None,
    ) -> None:
        self._repository = repository
        self._matcher = matcher or EligibilityMatcher()
        self._extractor = extractor or EligibilityExtractor()
        self._eligibility_by_program_id = eligibility_by_program_id or {}

    def get_program(self, program_id: str) -> Program:
        program = self._repository.get(program_id)
        if program is None:
            raise ProgramNotFoundError(program_id)
        return program

    def match_program(self, program_id: str, profile: UserProfile) -> MatchResponse:
        program = self.get_program(program_id)
        eligibility = self._eligibility_for(program)

        evaluation = self._matcher.match(eligibility, profile)
        return MatchResponse(
            program=program,
            match_status=evaluation.match_status,
            condition_results=evaluation.condition_results,
            evidence=evaluation.evidence,
            source=SourceInfo(
                source=program.source,
                source_url=str(program.source_url) if program.source_url else None,
                collected_at=(
                    program.collected_at.isoformat() if program.collected_at else None
                ),
            ),
            reason=evaluation.reason,
        )

    def get_program_eligibility(self, program_id: str) -> ProgramEligibility:
        return self._eligibility_for(self.get_program(program_id))

    def _eligibility_for(self, program: Program) -> ProgramEligibility:
        eligibility = self._eligibility_by_program_id.get(program.program_id)
        if eligibility is None:
            try:
                eligibility = self._extractor.extract(program)
            except Exception:
                # Extraction is an evidence-enrichment boundary. A failed baseline
                # must degrade to UNKNOWN instead of taking down program retrieval.
                eligibility = ProgramEligibility(
                    program_id=program.program_id,
                    source_url=program.source_url,
                    eligibility_extraction_status=ProgramExtractionStatus.UNKNOWN,
                )
        return eligibility
