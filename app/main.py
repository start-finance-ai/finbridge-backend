from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.programs import router as programs_router
from app.config import get_bizinfo_snapshot_path
from app.data.bizinfo_loader import BizinfoDataError
from app.data.program_repository import ProgramRepository
from app.services.program_service import ProgramService


def create_app() -> FastAPI:
    application = FastAPI(
        title="FinBridge Backend",
        version="0.1.0",
        description="Evidence-first support program matching backend.",
    )
    application.state.program_service = ProgramService(
        ProgramRepository(get_bizinfo_snapshot_path())
    )

    @application.exception_handler(BizinfoDataError)
    async def handle_bizinfo_data_error(
        request: Request, exc: BizinfoDataError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error_code": exc.error_code,
                "message": "Program snapshot is unavailable",
            },
        )

    application.include_router(health_router)
    application.include_router(programs_router)
    return application


app = create_app()
