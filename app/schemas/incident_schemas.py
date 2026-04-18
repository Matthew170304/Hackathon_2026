from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.domain.enums import (
    CauseCategory,
    HazardCategory,
    ProcessingStatus,
    RecurrenceFrequency,
    SeverityLevel,
)

class IncidentCreateRequest(BaseModel):
    external_case_id: str | None
    case_type: str | None
    location: str | None
    responsible_entity: str | None
    occurred_at: datetime | None
    title: str
    description: str
    activity: str | None
    severity_level: str | None
    recurrence_frequency: str | None
    classification: str | None
    cause_category: str | None
    cause: str | None
    immediate_actions: str | None
    action_description: str | None
    validation_description: str | None

class ProcessedIncidentResponse(BaseModel):
    id: UUID
    external_case_id: str | None
    processing_status: ProcessingStatus
    original_language: str | None
    translated_title: str | None
    translated_description: str | None
    cleaned_text: str
    hazard_category: HazardCategory
    hazard_confidence: float
    cause_category: CauseCategory
    cause_confidence: float
    severity_level: SeverityLevel
    severity_confidence: float
    recurrence_frequency: RecurrenceFrequency
    recurrence_confidence: float
    risk_score: int | None
    risk_level_label: str
    recommendation_summary: str | None
    created_at: datetime
    processed_at: datetime | None