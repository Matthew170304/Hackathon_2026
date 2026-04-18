from pydantic import BaseModel
from typing import List
import logging
logger = logging.getLogger(__name__)

from app.domain.enums import CauseCategory

from app.services.cause_keywords import CAUSE_KEYWORDS

from app.integrations.hazard_ai_client import HazardAIClient

ALLOWED_CAUSE_LABELS = {category.value for category in CauseCategory}


NO_MATCH_CONFIDENCE = 0.2

LOW_CONFIDENCE_THRESHOLD = 1
MEDIUM_CONFIDENCE_THRESHOLD = 2

LOW_CONFIDENCE_SCORE = 0.5
MEDIUM_CONFIDENCE_SCORE = 0.7
HIGH_CONFIDENCE_SCORE = 0.85

SOURCE_VALUE_CONFIDENCE = 0.95

AI_ACCEPT_THRESHOLD = 0.75
AI_FALLBACK_THRESHOLD = 0.65


class ClassificationResult(BaseModel):
    label: CauseCategory
    confidence: float
    explanation: str


class RuleClassificationResult(BaseModel):
    label: CauseCategory
    confidence: float
    explanation: str
    matched_keywords: list[str]


def normalize_source_cause_category(
    source_cause_category: str | None,
) -> CauseCategory | None:
    if source_cause_category is None:
        return None

    normalized_value = source_cause_category.strip()

    if not normalized_value:
        return None

    for category in CauseCategory:
        if normalized_value == category.value:
            return category

    return None


def build_source_classification_result(
    source_category: CauseCategory,
) -> ClassificationResult:
    return ClassificationResult(
        label=source_category,
        confidence=SOURCE_VALUE_CONFIDENCE,
        explanation="Used valid source cause category.",
    )


class CauseRuleClassifierService:
    def classify_cause_by_rules(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> RuleClassificationResult:
        source_category = normalize_source_cause_category(source_cause_category)

        if source_category is not None:
            return RuleClassificationResult(
                label=source_category,
                confidence=SOURCE_VALUE_CONFIDENCE,
                explanation="Used valid source cause category.",
                matched_keywords=[],
            )

        combined = f"{text or ''} {source_cause or ''}".lower()

        scores: dict[CauseCategory, int] = {}
        matches: dict[CauseCategory, list[str]] = {}

        for category, keywords in CAUSE_KEYWORDS.items():
            matched_keywords = [keyword for keyword in keywords if keyword in combined]

            if matched_keywords:
                scores[category] = len(matched_keywords)
                matches[category] = matched_keywords

        if not scores:
            return RuleClassificationResult(
                label=CauseCategory.UNKNOWN,
                confidence=NO_MATCH_CONFIDENCE,
                explanation="No cause keywords matched.",
                matched_keywords=[],
            )

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        matched_keywords = matches[best_category]

        if best_score == LOW_CONFIDENCE_THRESHOLD:
            confidence = LOW_CONFIDENCE_SCORE
        elif best_score == MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = MEDIUM_CONFIDENCE_SCORE
        else:
            confidence = HIGH_CONFIDENCE_SCORE

        explanation = f"Matched keywords: {', '.join(matched_keywords)}"

        return RuleClassificationResult(
            label=best_category,
            confidence=confidence,
            explanation=explanation,
            matched_keywords=matched_keywords,
        )


class HybridCauseClassifierService:
    def __init__(self) -> None:
        self.rule_classifier = CauseRuleClassifierService()
        self.ai_classifier = AICauseClassifierService(HazardAIClient())

    async def classify_cause(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> ClassificationResult:
        source_category = normalize_source_cause_category(source_cause_category)

        if source_category is not None:
            return build_source_classification_result(source_category)

        ai_result = await self.ai_classifier.classify_cause_ai(
            text=text,
            source_cause_category=source_cause_category,
            source_cause=source_cause,
        )

        if ai_result is not None:
            if ai_result.confidence >= AI_ACCEPT_THRESHOLD:
                return ai_result

            if ai_result.confidence >= AI_FALLBACK_THRESHOLD:
                return ai_result

        rule_result = self.rule_classifier.classify_cause_by_rules(
            text=text,
            source_cause_category=source_cause_category,
            source_cause=source_cause,
        )

        return ClassificationResult(
            label=rule_result.label,
            confidence=rule_result.confidence,
            explanation=rule_result.explanation,
        )


class AICauseClassifierService:
    def __init__(self, ai_client: HazardAIClient) -> None:
        self.ai_client = ai_client

    async def classify_cause_ai(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> ClassificationResult | None:
        source_category = normalize_source_cause_category(source_cause_category)

        if source_category is not None:
            return build_source_classification_result(source_category)

        user_prompt = (
            f"Incident text:\n{text}\n\n"
            f"Source cause category:\n{source_cause_category or ''}\n\n"
            f"Source cause:\n{source_cause or ''}"
        )

        from app.services.cause_prompts import CAUSE_CLASSIFICATION_SYSTEM_PROMPT
        system_prompt = CAUSE_CLASSIFICATION_SYSTEM_PROMPT

        try:
            response = await self.ai_client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
            )

            logger.info("AI raw_text=%s", response.raw_text)
            logger.info("AI data=%s", response.data)
        except Exception:
            return None

        data = response.data

        label = data.get("label")
        confidence = data.get("confidence")
        explanation = data.get("explanation")

        if (
            label not in ALLOWED_CAUSE_LABELS
            or not isinstance(confidence, (int, float))
            or not (0.0 <= confidence <= 1.0)
            or not isinstance(explanation, str)
        ):
            return None

        return ClassificationResult(
            label=CauseCategory(label),
            confidence=float(confidence),
            explanation=explanation,
        )