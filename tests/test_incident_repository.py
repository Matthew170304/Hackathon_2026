from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.domain.enums import (
    CauseCategory,
    HazardCategory,
    RecurrenceFrequency,
    SeverityLevel,
)
from app.repositories.batch_repository import BatchRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident_schemas import IncidentCreateRequest
from app.schemas.processing_schemas import ProcessingResult


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_raw_incident_saves_source_fields() -> None:
    session = create_test_session()
    repository = IncidentRepository(session)

    incident = IncidentCreateRequest(
        external_case_id="188616",
        case_type="EHS - Near miss",
        location="Denmark - Christiansfeld - Ravnhavevej 6-8",
        responsible_entity="Danfoss Climate Solutions",
        occurred_at=datetime(2025, 11, 17),
        title="Operator trips",
        description="Operator trips over marking in walking path.",
        activity="Walking / working surfaces",
        severity_level=None,
        recurrence_frequency="6 months - 1 year",
        classification="NMI",
        cause_category="Workplace Design",
        cause="Lay-out inadequate/inappropriate",
        immediate_actions="Moved marking.",
        action_description=None,
        validation_description=None,
    )

    saved = repository.create_raw_incident(incident, source="api")

    assert saved.id is not None
    assert saved.external_case_id == "188616"
    assert saved.country == "Denmark"
    assert saved.site == "Christiansfeld"
    assert saved.recurrence_frequency_source == "6 months - 1 year"


def test_save_and_get_processing_result() -> None:
    session = create_test_session()
    repository = IncidentRepository(session)

    incident = IncidentCreateRequest(
        external_case_id="1",
        case_type=None,
        location="Denmark - Nordborg - Nordborgvej 81",
        responsible_entity=None,
        occurred_at=datetime(2025, 1, 1),
        title="Wet floor",
        description="Wet floor caused slip risk.",
        activity="Walking / working surfaces",
        severity_level=None,
        recurrence_frequency=None,
        classification=None,
        cause_category=None,
        cause=None,
        immediate_actions=None,
        action_description=None,
        validation_description=None,
    )
    saved_incident = repository.create_raw_incident(incident, source="api")

    result = ProcessingResult(
        cleaned_text="Wet floor caused slip risk.",
        original_language="en",
        translated_title="Wet floor",
        translated_description="Wet floor caused slip risk.",
        hazard_category=HazardCategory.PHYSICAL,
        hazard_confidence=0.9,
        hazard_explanation="Mentions wet floor and slip risk.",
        cause_category=CauseCategory.HOUSEKEEPING,
        cause_confidence=0.8,
        cause_explanation="Wet floor points to housekeeping issue.",
        severity_level=SeverityLevel.LOW,
        severity_confidence=0.7,
        severity_explanation="Slip risk without injury.",
        recurrence_frequency=RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS,
        recurrence_confidence=0.65,
        recurrence_explanation="Temporary condition.",
        risk_score=20,
        risk_level_label="Medium",
        recommendation_summary="Dry area and add visible wet floor signs.",
        needs_human_review=True,
    )

    saved_processed = repository.save_processing_result(saved_incident.id, result)
    fetched = repository.get_processed_incident(saved_incident.id)

    assert saved_processed.hazard_category == "Physical Hazards"
    assert saved_processed.processing_status == "needs_review"
    assert fetched is not None
    assert fetched.incident.external_case_id == "1"


def test_batch_repository_tracks_progress() -> None:
    session = create_test_session()
    repository = BatchRepository(session)

    batch = repository.create_upload_batch("incidents.xlsx", total_rows=10)
    updated = repository.update_progress(
        batch_id=batch.id,
        processed_rows=8,
        failed_rows=2,
        status="processed",
    )

    assert updated.total_rows == 10
    assert updated.processed_rows == 8
    assert updated.failed_rows == 2
    assert updated.finished_at is not None
