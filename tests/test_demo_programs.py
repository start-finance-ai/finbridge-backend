from datetime import date

import pytest

from app.config import BIZINFO_BOOTSTRAP_SNAPSHOT
from app.data.program_repository import ProgramRepository, normalize_bizinfo_program
from app.retrieval.program_retrieval import ProgramRetrievalService
from app.schemas.matching import MatchStatus, UserProfile
from app.schemas.retrieval import ProgramSearchRequest
from app.services.program_service import ProgramService
from app.utils.date_parser import ApplicationStatus, calculate_application_availability


def demo_service() -> ProgramService:
    return ProgramService(ProgramRepository(BIZINFO_BOOTSTRAP_SNAPSHOT))


def test_demo_records_have_explicit_provenance_and_no_application_links() -> None:
    programs = demo_service().list_programs()
    assert len(programs) == 6
    for program in programs:
        assert program.source == "DEMO"
        assert program.program_name.startswith("[데모]")
        assert program.source_url is None
        assert program.document_url is None
        assert program.contact_raw is None


@pytest.mark.parametrize("age", [19, 28, 39])
def test_demo_matching_accepts_age_boundaries(age: int) -> None:
    result = demo_service().match_program(
        "DEMO_002",
        UserProfile(region="대구", business_region="대구", age=age, pre_founder=True),
    )
    assert result.match_status is MatchStatus.MATCH
    assert result.evidence
    assert result.source.source == "DEMO"


@pytest.mark.parametrize("age", [18, 40])
def test_demo_matching_rejects_out_of_range_age(age: int) -> None:
    result = demo_service().match_program(
        "DEMO_002",
        UserProfile(region="대구", business_region="대구", age=age, pre_founder=True),
    )
    assert result.match_status is MatchStatus.NO_MATCH


def test_demo_retrieval_excludes_explicit_other_region() -> None:
    result = ProgramRetrievalService(demo_service()).search(
        ProgramSearchRequest(query="창업", region="대구", limit=20)
    )
    ids = {item.program.program_id for item in result.results}
    assert "DEMO_002" in ids
    assert "DEMO_001" not in ids
    assert all(item.source == "DEMO" for item in result.results)


def test_closed_demo_period_is_not_open() -> None:
    program = demo_service().get_program("DEMO_006")
    availability = calculate_application_availability(
        deadline_type=program.deadline_type,
        apply_start=program.apply_start,
        apply_end=program.apply_end,
        today=date(2026, 10, 2),
    )
    assert availability.status is ApplicationStatus.CLOSED


def test_external_api_normalization_keeps_bizinfo_source() -> None:
    program = normalize_bizinfo_program(
        {"pblancId": "TEST_EXTERNAL", "pblancNm": "외부 입력 형식 검증"}
    )
    assert program.source == "BIZINFO"
