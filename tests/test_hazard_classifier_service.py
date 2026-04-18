import os

import pytest

from app.domain.enums import HazardCategory
from app.integrations.hazard_ai_client import HazardAIClient
from app.services.hazard_classifier_service import AIHazardClassifierService


pytestmark = pytest.mark.integration


def _has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _has_api_key(),
    reason="OPENAI_API_KEY not set; skipping real API integration test.",
)
async def test_ai_hazard_classifier_real_api_vehicle_traffic() -> None:
    ai_client = HazardAIClient()
    classifier = AIHazardClassifierService(ai_client=ai_client)

    result = await classifier.classify_hazard_ai(
        text="A forklift reversing in the warehouse nearly hit a pedestrian crossing the aisle.",
        activity="Internal transport in production area",
    )

    assert result is not None
    assert result.label == HazardCategory.VEHICLE_TRAFFIC
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.explanation, str)
    assert result.explanation.strip() != ""


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _has_api_key(),
    reason="OPENAI_API_KEY not set; skipping real API integration test.",
)
async def test_ai_hazard_classifier_real_api_electrical() -> None:
    ai_client = HazardAIClient()
    classifier = AIHazardClassifierService(ai_client=ai_client)

    result = await classifier.classify_hazard_ai(
        text="The technician received an electric shock after touching exposed wiring on faulty equipment.",
        activity="Maintenance inspection",
    )

    assert result is not None
    assert result.label == HazardCategory.ELECTRICAL
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.explanation, str)
    assert result.explanation.strip() != ""