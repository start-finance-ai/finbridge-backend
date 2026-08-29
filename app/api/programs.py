from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.retrieval.program_retrieval import ProgramRetrievalService
from app.schemas.matching import (
    BusinessStatus,
    MatchRequest,
    MatchResponse,
    UserType,
)
from app.schemas.program import Program
from app.schemas.retrieval import ProgramSearchRequest, ProgramSearchResponse
from app.services.program_service import ProgramNotFoundError, ProgramService


router = APIRouter(prefix="/programs", tags=["programs"])


def _service(request: Request) -> ProgramService:
    return request.app.state.program_service


@router.get("", response_model=ProgramSearchResponse)
def search_programs(
    request: Request,
    query: str | None = Query(default=None, min_length=1, max_length=500),
    region: str | None = Query(default=None, min_length=1, max_length=100),
    business_status: BusinessStatus | None = None,
    user_type: UserType | None = None,
    category: str | None = Query(default=None, min_length=1, max_length=100),
    provider: str | None = Query(default=None, min_length=1, max_length=200),
    industry: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
) -> ProgramSearchResponse:
    service: ProgramRetrievalService = request.app.state.program_retrieval_service
    return service.search(
        ProgramSearchRequest(
            query=query,
            region=region,
            business_status=business_status,
            user_type=user_type,
            category=category,
            provider=provider,
            industry=industry,
            limit=limit,
        )
    )


@router.get("/{program_id}", response_model=Program)
def get_program(program_id: str, request: Request) -> Program:
    try:
        return _service(request).get_program(program_id)
    except ProgramNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROGRAM_NOT_FOUND", "message": "Program not found"},
        ) from exc


@router.post("/match", response_model=MatchResponse)
def match_program(payload: MatchRequest, request: Request) -> MatchResponse:
    try:
        return _service(request).match_program(payload.program_id, payload.profile)
    except ProgramNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROGRAM_NOT_FOUND", "message": "Program not found"},
        ) from exc
