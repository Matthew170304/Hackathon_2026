from app.services.cause.ai_classifier import AICauseClassifierService
from app.services.cause.rule_classifier import CauseRuleClassifierService
from app.services.cause.source_values import (
    build_source_classification_result,
    normalize_source_cause_category,
)
from app.services.models.cause_classifier_models import ClassificationResult


AI_ACCEPT_THRESHOLD = 0.75
AI_FALLBACK_THRESHOLD = 0.65


class HybridCauseClassifierService:
    def __init__(self) -> None:
        from app.integrations.hazard_ai_client import HazardAIClient

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
