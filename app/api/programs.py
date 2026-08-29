from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.matching import MatchRequest, MatchResponse
from app.schemas.program import Program
from app.services.program_service import ProgramNotFoundError, ProgramService


router = APIRouter(prefix="/programs", tags=["programs"])


def _service(request: Request) -> ProgramService:
    return request.app.state.program_service


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
