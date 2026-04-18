import asyncio
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.models import Base
from app.domain.enums import (
    CauseCategory,
    HazardCategory,
    RecurrenceFrequency,
    SeverityLevel,
)
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident_schemas import IncidentCreateRequest
from app.schemas.processing_schemas import ProcessingResult
from app.services.analytics import AnalyticsService


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_strategic_recommendation_accounts_for_observation_bias(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "mock")
    get_settings.cache_clear()

    session = create_test_session()
    repository = IncidentRepository(session)

    incident = IncidentCreateRequest(
        external_case_id="strategic-1",
        location="Denmark - Nordborg - Nordborgvej 81",
        occurred_at=datetime(2025, 6, 1),
        title="Machine guard missing",
        description="Machine guard was removed from rotating part during adjustment.",
        activity="Machining",
        recurrence_frequency="0 - 14 days",
    )
    saved = repository.create_raw_incident(incident, source="test")
    repository.save_processing_result(
        saved.id,
        ProcessingResult(
            cleaned_text="Machine guard missing.",
            original_language="en",
            translated_title="Machine guard missing",
            translated_description="Machine guard was removed.",
            hazard_category=HazardCategory.MECHANICAL_EQUIPMENT,
            hazard_confidence=0.9,
            hazard_explanation="Machine guard.",
            cause_category=CauseCategory.PROCEDURES,
            cause_confidence=0.8,
            cause_explanation="Procedure issue.",
            severity_level=SeverityLevel.HIGH,
            severity_confidence=0.8,
            severity_explanation="High severity.",
            recurrence_frequency=RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS,
            recurrence_confidence=0.8,
            recurrence_explanation="Frequent.",
            risk_score=125,
            risk_level_label="Critical",
            recommendation_summary="Fix guarding.",
            needs_human_review=True,
        ),
    )

    result = asyncio.run(
        AnalyticsService(session).generate_strategic_recommendation(
            date_from=date(2025, 1, 1),
            date_to=date(2025, 12, 31),
            location="Nordborg",
        )
    )

    assert result.incident_count == 1
    assert result.ai_generated is False
    assert "low count" in result.observability_bias_note.lower() or "low risk" in result.observability_bias_note.lower()
    assert result.hidden_risk_hypotheses
    assert result.recommended_actions

    get_settings.cache_clear()
