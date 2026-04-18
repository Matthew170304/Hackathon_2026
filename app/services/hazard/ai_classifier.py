import logging
from typing import TYPE_CHECKING

from app.domain.enums import HazardCategory
from app.services.hazard.models import ClassificationResult


if TYPE_CHECKING:
    from app.integrations.hazard_ai_client import HazardAIClient


logger = logging.getLogger(__name__)

ALLOWED_HAZARD_LABELS = {category.value for category in HazardCategory}


class AIHazardClassifierService:
    def __init__(self, ai_client: 'HazardAIClient') -> None:
        self.ai_client = ai_client

    async def classify_hazard_ai(
        self,
        text: str,
        activity: str | None,
    ) -> ClassificationResult | None:
        from app.services.hazard.prompts import HAZARD_CLASSIFICATION_SYSTEM_PROMPT

        user_prompt = (
            f'Incident text:\n{text}\n\n'
            f'Activity:\n{activity or ""}'
        )

        try:
            response = await self.ai_client.complete_json(
                system_prompt=HAZARD_CLASSIFICATION_SYSTEM_PROMPT,
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
