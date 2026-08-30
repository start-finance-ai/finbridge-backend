from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.calculation.sales_analysis import calculate_sales_analysis
from app.data.sales_upload import (
    MAX_FILE_BYTES,
    SalesUploadError,
    parse_sales_upload,
)
from app.schemas.sales_analysis import SalesAnalysisResponse


router = APIRouter(prefix="/sales-analysis", tags=["sales-analysis"])


@router.post("/analyze", response_model=SalesAnalysisResponse)
async def analyze(file: UploadFile = File(...)) -> SalesAnalysisResponse:
    try:
        if file.size is not None and file.size > MAX_FILE_BYTES:
            raise SalesUploadError(
                "FILE_TOO_LARGE",
                "Uploaded file exceeds the 5 MB limit",
                status_code=413,
                context={"max_file_bytes": MAX_FILE_BYTES},
            )
        content = await file.read(MAX_FILE_BYTES + 1)
        parsed = parse_sales_upload(filename=file.filename, content=content)
        return calculate_sales_analysis(parsed)
    except SalesUploadError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_detail(),
        ) from exc
    finally:
        await file.close()
