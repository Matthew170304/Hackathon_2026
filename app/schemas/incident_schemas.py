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
    external_case_id: str | None = None
    case_type: str | None = None
    location: str | None = None
    responsible_entity: str | None = None
    occurred_at: datetime | None = None
    title: str | None = None
    description: str | None = None
    activity: str | None = None
    severity_level: str | None = None
    recurrence_frequency: str | None = None
    classification: str | None = None
    cause_category: str | None = None
    cause: str | None = None
    immediate_actions: str | None = None
    action_description: str | None = None
    validation_description: str | None = None

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
