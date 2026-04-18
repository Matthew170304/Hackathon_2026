import logging
from typing import TYPE_CHECKING

from app.domain.enums import CauseCategory
from app.services.cause.source_values import (
    build_source_classification_result,
    normalize_source_cause_category,
)
from app.services.models.cause_classifier_models import ClassificationResult


if TYPE_CHECKING:
    from app.integrations.hazard_ai_client import HazardAIClient


logger = logging.getLogger(__name__)

ALLOWED_CAUSE_LABELS = {category.value for category in CauseCategory}


class AICauseClassifierService:
    def __init__(self, ai_client: 'HazardAIClient') -> None:
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

        from app.services.cause.prompts import CAUSE_CLASSIFICATION_SYSTEM_PROMPT

        user_prompt = (
            f'Incident text:\n{text}\n\n'
            f'Source cause category:\n{source_cause_category or ""}\n\n'
            f'Source cause:\n{source_cause or ""}'
        )

        try:
            response = await self.ai_client.complete_json(
                system_prompt=CAUSE_CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )

            logger.info('AI raw_text=%s', response.raw_text)
            logger.info('AI data=%s', response.data)
        except Exception:
            return None

        data = response.data
        label = data.get('label')
        confidence = data.get('confidence')
        explanation = data.get('explanation')

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
