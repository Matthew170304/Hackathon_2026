from pydantic import BaseModel
from typing import List
import logging
logger = logging.getLogger(__name__)

from app.domain.enums import HazardCategory

from app.services.hazard_keywords import HAZARD_KEYWORDS

from app.integrations.hazard_ai_client import HazardAIClient

ALLOWED_HAZARD_LABELS = {c.value for c in HazardCategory}


NO_MATCH_CONFIDENCE = 0.2

LOW_CONFIDENCE_THRESHOLD = 1
MEDIUM_CONFIDENCE_THRESHOLD = 2

LOW_CONFIDENCE_SCORE = 0.5
MEDIUM_CONFIDENCE_SCORE = 0.7
HIGH_CONFIDENCE_SCORE = 0.85

AI_ACCEPT_THRESHOLD = 0.75
AI_FALLBACK_THRESHOLD = 0.65


class ClassificationResult(BaseModel):
    label: HazardCategory
    confidence: float
    explanation: str


class RuleClassificationResult(BaseModel):
    label: HazardCategory
    confidence: float
    explanation: str
    matched_keywords: List[str]


class HazardRuleClassifierService:
    def classify_hazard_by_rules(
        self,
        text: str,
        activity: str | None,
    ) -> RuleClassificationResult:

        combined = f"{text or ''} {activity or ''}".lower()

        scores: dict[HazardCategory, int] = {}
        matches: dict[HazardCategory, list[str]] = {}

        # keyword matching
        for category, keywords in HAZARD_KEYWORDS.items():
            matched_keywords = [kw for kw in keywords if kw in combined]

            if matched_keywords:
                scores[category] = len(matched_keywords)
                matches[category] = matched_keywords

        # no matches
        if not scores:
            return RuleClassificationResult(
                label=HazardCategory.UNKNOWN,
                confidence=NO_MATCH_CONFIDENCE,
                explanation="No hazard keywords matched.",
                matched_keywords=[],
            )

        # best category
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        matched_keywords = matches[best_category]

        # confidence mapping
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


class AIHazardClassifierService:
    def __init__(self, ai_client: HazardAIClient) -> None:
        self.ai_client = ai_client

    async def classify_hazard_ai(
        self,
        text: str,
        activity: str | None,
    ) -> ClassificationResult | None:
        """
        Returns ClassificationResult if valid.
        Returns None if AI response is invalid → triggers fallback.
        """

        from app.services.hazard_prompts import HAZARD_CLASSIFICATION_SYSTEM_PROMPT
        system_prompt = HAZARD_CLASSIFICATION_SYSTEM_PROMPT

        user_prompt = (
            f"Incident text:\n{text}\n\n"
            f"Activity:\n{activity or ''}"
        )

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

        # --- validation ---
        label = data.get("label")
        confidence = data.get("confidence")
        explanation = data.get("explanation")

        if (
            label not in ALLOWED_HAZARD_LABELS
            or not isinstance(confidence, (int, float))
            or not (0.0 <= confidence <= 1.0)
            or not isinstance(explanation, str)
        ):
            return None

        return ClassificationResult(
            label=HazardCategory(label),
            confidence=float(confidence),
            explanation=explanation,
        )


class HybridHazardClassifierService:
    def __init__(self) -> None:
        self.rule_classifier = HazardRuleClassifierService()
        self.ai_classifier = AIHazardClassifierService(HazardAIClient())

    async def classify_hazard(
        self,
        text: str,
        activity: str | None,
    ) -> ClassificationResult:
        """
        Hybrid hazard classification.

        Flow:
        1. Try AI
        2. If valid → decide based on confidence
        3. Else → fallback to rules
        """

        # --- 1. Try AI ---
        ai_result = await self.ai_classifier.classify_hazard_ai(
            text=text,
            activity=activity,
        )

        # --- 2. Decide ---
        if ai_result is not None:
            if ai_result.confidence >= AI_ACCEPT_THRESHOLD:
                return ai_result

            if ai_result.confidence >= AI_FALLBACK_THRESHOLD:
                return ai_result  # weaker but acceptable

        # --- 3. Fallback ---
        rule_result = self.rule_classifier.classify_hazard_by_rules(
            text=text,
            activity=activity,
        )

        return ClassificationResult(
            label=rule_result.label,
            confidence=rule_result.confidence,
            explanation=rule_result.explanation,
        )