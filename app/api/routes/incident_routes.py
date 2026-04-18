from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import ProcessedIncident
from app.domain.enums import (
    CauseCategory,
    HazardCategory,
    ProcessingStatus,
    RecurrenceFrequency,
    SeverityLevel,
)
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident_schemas import IncidentCreateRequest, ProcessedIncidentResponse
from app.services.emailnotificationservice import EmailNotificationService, EmailSendError
from app.services.incident_processing import IncidentProcessingService


router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=ProcessedIncidentResponse)
async def create_incident(
    incident: IncidentCreateRequest,
    session: Session = Depends(get_db_session),
) -> ProcessedIncidentResponse:
    repository = IncidentRepository(session)
    raw_incident = repository.create_raw_incident(incident, source="api")
    result = await IncidentProcessingService().process_incident(incident)
    processed = repository.save_processing_result(raw_incident.id, result)
    processed.incident = raw_incident
    return _to_response(processed)


@router.get("/{incident_id}", response_model=ProcessedIncidentResponse)
async def get_incident(
    incident_id: UUID,
    session: Session = Depends(get_db_session),
) -> ProcessedIncidentResponse:
    processed = IncidentRepository(session).get_processed_incident(incident_id)
    if processed is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _to_response(processed)


@router.post("/{incident_id}/notify-manager")
async def notify_manager(
    incident_id: UUID,
    session: Session = Depends(get_db_session),
) -> dict[str, str]:
    service = EmailNotificationService(session)
    try:
        service.send_manager_notification_for_incident(incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmailSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent"}


def _to_response(processed: ProcessedIncident) -> ProcessedIncidentResponse:
    incident = processed.incident
    return ProcessedIncidentResponse(
        id=UUID(processed.incident_id),
        external_case_id=incident.external_case_id if incident else None,
        processing_status=ProcessingStatus(processed.processing_status),
        original_language=processed.original_language,
        translated_title=processed.translated_title,
        translated_description=processed.translated_description,
        cleaned_text=processed.cleaned_text,
        hazard_category=HazardCategory(processed.hazard_category),
        hazard_confidence=processed.hazard_confidence,
        cause_category=CauseCategory(processed.cause_category),
        cause_confidence=processed.cause_confidence,
        severity_level=SeverityLevel(processed.severity_level),
        severity_confidence=processed.severity_confidence,
        recurrence_frequency=RecurrenceFrequency(processed.recurrence_frequency),
        recurrence_confidence=processed.recurrence_confidence,
        risk_score=processed.risk_score,
        risk_level_label=processed.risk_level_label,
        recommendation_summary=processed.recommendation_summary,
        created_at=processed.created_at,
        processed_at=processed.processed_at,
    )
