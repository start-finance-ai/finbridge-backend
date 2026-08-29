from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.ai.provider import AIProvider, OpenAIProvider
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.programs import router as programs_router
from app.api.risk import router as risk_router
from app.config import get_bizinfo_snapshot_path, get_openai_settings
from app.data.bizinfo_loader import BizinfoDataError
from app.data.program_repository import ProgramRepository
from app.retrieval.program_retrieval import ProgramRetrievalService
from app.services.chat_service import ChatService
from app.services.program_service import ProgramService


def create_app(ai_provider: AIProvider | None = None) -> FastAPI:
    application = FastAPI(
        title="FinBridge Backend",
        version="0.1.0",
        description="Evidence-first support program matching backend.",
    )
    program_service = ProgramService(
        ProgramRepository(get_bizinfo_snapshot_path())
    )
    application.state.program_service = program_service
    program_retrieval_service = ProgramRetrievalService(program_service)
    application.state.program_retrieval_service = program_retrieval_service
    application.state.chat_service = ChatService(
        program_service,
        ai_provider or OpenAIProvider(get_openai_settings()),
        program_retrieval_service,
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
    application.include_router(chat_router)
    application.include_router(programs_router)
    application.include_router(risk_router)
    return application


app = create_app()
