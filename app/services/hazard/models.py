from pydantic import BaseModel

from app.domain.enums import HazardCategory


class ClassificationResult(BaseModel):
    label: HazardCategory
    confidence: float
    explanation: str


class RuleClassificationResult(BaseModel):
    label: HazardCategory
    confidence: float
    explanation: str
    matched_keywords: list[str]
