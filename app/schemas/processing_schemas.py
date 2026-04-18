from pydantic import BaseModel
from app.domain.enums import (
    CauseCategory,
    HazardCategory,
    ProcessingStatus,
    RecurrenceFrequency,
    SeverityLevel,
)


class ProcessingResult(BaseModel):
    cleaned_text: str
    original_language: str | None
    translated_title: str | None
    translated_description: str | None
    hazard_category: HazardCategory
    hazard_confidence: float
    hazard_explanation: str
    cause_category: CauseCategory
    cause_confidence: float
    cause_explanation: str
    severity_level: SeverityLevel
    severity_confidence: float
    severity_explanation: str
    recurrence_frequency: RecurrenceFrequency
    recurrence_confidence: float
    recurrence_explanation: str
    risk_score: int | None
    risk_level_label: str
    recommendation_summary: str
    needs_human_review: bool