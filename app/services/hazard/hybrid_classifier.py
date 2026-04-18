from app.services.hazard.ai_classifier import AIHazardClassifierService
from app.services.hazard.rule_classifier import HazardRuleClassifierService
from app.services.hazard.models import ClassificationResult


AI_ACCEPT_THRESHOLD = 0.75
AI_FALLBACK_THRESHOLD = 0.65


class HybridHazardClassifierService:
    def __init__(self) -> None:
        from app.integrations.hazard_ai_client import HazardAIClient

        self.rule_classifier = HazardRuleClassifierService()
        self.ai_classifier = AIHazardClassifierService(HazardAIClient())

    async def classify_hazard(
        self,
        text: str,
        activity: str | None,
    ) -> ClassificationResult:
        ai_result = await self.ai_classifier.classify_hazard_ai(
            text=text,
            activity=activity,
        )

        if ai_result is not None:
            if ai_result.confidence >= AI_ACCEPT_THRESHOLD:
                return ai_result

            if ai_result.confidence >= AI_FALLBACK_THRESHOLD:
                return ai_result

        rule_result = self.rule_classifier.classify_hazard_by_rules(
            text=text,
            activity=activity,
        )

        return ClassificationResult(
            label=rule_result.label,
            confidence=rule_result.confidence,
            explanation=rule_result.explanation,
        )
