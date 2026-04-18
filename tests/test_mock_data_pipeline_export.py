import csv
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from app.repositories.batch_repository import BatchRepository
from app.repositories.incident_repository import IncidentRepository
from app.services.analytics import AnalyticsService
from app.services.excel_ingestion import ExcelIngestionService
from app.services.incident_processing import IncidentProcessingService


ROOT_DIR = Path(__file__).resolve().parents[1]
MOCK_DATA_DIR = ROOT_DIR / "mock_data"
RAW_SAMPLE_PATH = MOCK_DATA_DIR / "raw_incidents_unprocessed_mock.csv"
EXPORT_PATH = MOCK_DATA_DIR / "processed_incidents_export.csv"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_raw_mock_data_pipeline_saves_to_db_and_exports_finished_data(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'mock_pipeline.db'}")
    Base.metadata.create_all(engine)

    session = Session(engine)
    try:
        frame = pd.read_csv(RAW_SAMPLE_PATH)
        batch = BatchRepository(session).create_upload_batch(
            RAW_SAMPLE_PATH.name,
            total_rows=len(frame),
            source="mock_csv",
        )
        ingestion_service = ExcelIngestionService(session)
        incident_repository = IncidentRepository(session)
        processing_service = IncidentProcessingService()

        processed_rows = 0
        failed_rows = 0
        errors: list[str] = []

        for index, row in frame.iterrows():
            try:
                incident = ingestion_service.map_row_to_incident(row)
                raw_incident = incident_repository.create_raw_incident(
                    incident,
                    source="mock_csv",
                    source_batch_id=batch.id,
                )
                result = await processing_service.process_incident(incident)
                incident_repository.save_processing_result(raw_incident.id, result)
                processed_rows += 1
            except Exception as exc:
                failed_rows += 1
                errors.append(f"row {index + 2}: {exc}")

        BatchRepository(session).update_progress(
            batch.id,
            processed_rows=processed_rows,
            failed_rows=failed_rows,
            status="processed" if failed_rows == 0 else "failed",
        )

        assert failed_rows == 0, "\n".join(errors)
        assert processed_rows == len(frame)

        records = AnalyticsService(session).list_powerbi_incidents()
        rows = [record.model_dump() for record in records]
        rows.sort(key=lambda value: value["external_case_id"] or "")

        assert len(rows) == len(frame)
        assert all(row["hazard_category"] for row in rows)
        assert all(row["severity_level"] for row in rows)
        assert all(row["recommendation_summary"] for row in rows)

        EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EXPORT_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        assert EXPORT_PATH.exists()
        assert EXPORT_PATH.stat().st_size > 0
    finally:
        session.close()
