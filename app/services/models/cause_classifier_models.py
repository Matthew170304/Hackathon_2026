from pydantic import BaseModel

from app.domain.enums import CauseCategory


class ClassificationResult(BaseModel):
    label: CauseCategory
    confidence: float
    explanation: str


class RuleClassificationResult(BaseModel):
    label: CauseCategory
    confidence: float
    explanation: str
    matched_keywords: list[str]
