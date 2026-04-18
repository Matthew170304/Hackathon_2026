from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.upload_schemas import ExcelIngestionResult
from app.services.excel_ingestion import ExcelIngestionService


router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/excel", response_model=ExcelIngestionResult)
async def upload_excel(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> ExcelIngestionResult:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")

    file_bytes = await file.read()
    return await ExcelIngestionService(session).process_excel_file(file_bytes, file.filename)
