from pydantic import BaseModel

from app.domain.enums import RecurrenceFrequency, SeverityLevel


class SeverityInferenceResult(BaseModel):
    severity_level: SeverityLevel
    confidence: float
    explanation: str
    used_source_value: bool


class RecurrenceInferenceResult(BaseModel):
    recurrence_frequency: RecurrenceFrequency
    confidence: float
    explanation: str
    used_source_value: bool


__all__ = ["RecurrenceInferenceResult", "SeverityInferenceResult"]
