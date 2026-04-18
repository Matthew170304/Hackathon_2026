from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.repositories.batch_repository import BatchRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident_schemas import IncidentCreateRequest
from app.schemas.upload_schemas import ExcelIngestionResult, ExcelRowError
from app.services.incident_processing import IncidentProcessingService


class ExcelIngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.batch_repository = BatchRepository(session)
        self.incident_repository = IncidentRepository(session)
        self.processing_service = IncidentProcessingService()

    def read_excel_file(
        self,
        file_bytes: bytes,
        sheet_name: str | None = None,
    ) -> pd.DataFrame:
        return pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name or 0)

    def map_row_to_incident(self, row: pd.Series) -> IncidentCreateRequest:
        data = {str(key).strip().lower(): self._empty_to_none(value) for key, value in row.items()}

        return IncidentCreateRequest(
            external_case_id=self._first(data, "case no.", "case no", "case id", "id"),
            case_type=self._first(data, "case type", "type"),
            location=self._first(data, "location", "site", "site location"),
            responsible_entity=self._first(data, "responsible entity", "responsible unit", "business unit"),
            occurred_at=self._parse_datetime(
                self._first(data, "occurred at", "incident date", "date and time", "date", "created")
            ),
            title=self._first(data, "title", "case title", "short description"),
            description=self._first(data, "description", "case description", "event description"),
            activity=self._first(data, "activity", "work activity"),
            severity_level=self._first(data, "severity", "severity level", "risk severity"),
            recurrence_frequency=self._first(
                data,
                "recurrence",
                "frequency",
                "recurrence frequency",
                "most probable recurrence frequency",
            ),
            classification=self._first(data, "classification", "case classification"),
            cause_category=self._first(data, "cause category", "root cause category"),
            cause=self._first(data, "cause", "root cause"),
            immediate_actions=self._first(data, "immediate actions", "immediate action"),
            action_description=self._first(data, "action description", "corrective action"),
            validation_description=self._first(
                data,
                "validation description",
                "validation description(actions)",
                "validation",
            ),
        )

    async def process_excel_file(
        self,
        file_bytes: bytes,
        file_name: str,
    ) -> ExcelIngestionResult:
        frame = self.read_excel_file(file_bytes)
        batch = self.batch_repository.create_upload_batch(file_name, total_rows=len(frame))
        processed_rows = 0
        failed_rows = 0
        errors: list[ExcelRowError] = []

        for index, row in frame.iterrows():
            try:
                incident = self.map_row_to_incident(row)
                raw_incident = self.incident_repository.create_raw_incident(
                    incident,
                    source="excel",
                    source_batch_id=batch.id,
                )
                result = await self.processing_service.process_incident(incident)
                self.incident_repository.save_processing_result(raw_incident.id, result)
                processed_rows += 1
            except Exception as exc:
                failed_rows += 1
                errors.append(ExcelRowError(row_number=int(index) + 2, error=str(exc)))

        status = "processed" if failed_rows == 0 else "failed" if processed_rows == 0 else "processed"
        self.batch_repository.update_progress(
            batch.id,
            processed_rows=processed_rows,
            failed_rows=failed_rows,
            status=status,
        )

        return ExcelIngestionResult(
            batch_id=batch.id,
            file_name=file_name,
            total_rows=len(frame),
            processed_rows=processed_rows,
            failed_rows=failed_rows,
            status=status,
            errors=errors,
        )

    @staticmethod
    def _empty_to_none(value: Any) -> str | None:
        if pd.isna(value):
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _first(data: dict[str, str | None], *names: str) -> str | None:
        for name in names:
            value = data.get(name)
            if value:
                return value
        return None

    @staticmethod
    def _parse_datetime(value: str | None):
        if value is None:
            return None
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
