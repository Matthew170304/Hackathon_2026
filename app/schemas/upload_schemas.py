from pydantic import BaseModel


class ExcelRowError(BaseModel):
    row_number: int
    error: str


class ExcelIngestionResult(BaseModel):
    batch_id: str
    file_name: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    status: str
    errors: list[ExcelRowError] = []
