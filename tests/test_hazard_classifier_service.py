import os

import pytest

from app.domain.enums import HazardCategory
from app.integrations.hazard_ai_client import HazardAIClient
from app.services.hazard import AIHazardClassifierService


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
        text="The side door's site, by the shop floor production entry, had the floor soapery for cleaning purposes. A functionary of the cleaning department, while passing through the slippery route, tripped and fell by the metal door, hitting their head lightly on the flat surface. The functionary did not had any injuries, just minor local aches. The case was taken immediately to the RCPS Board for discussion. The area did not have the Wet Floor board.",
        activity="After the incident, the area was isolated as wet floor, and quickly dried out. An outside board that says the material of the floor is slippery has been set too.",
    )

    assert result is not None
    assert result.label == HazardCategory.ERGONOMIC
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
        text="Operatør snubler over afmærkning der delvis står på gågang",
        activity="Afmærkning flyttet væk fra gågang. indskærpet ved ugentlige møder, samt i relevante afdeling.",
    )

    assert result is not None
    assert result.label == HazardCategory.ERGONOMIC
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.explanation, str)
    assert result.explanation.strip() != ""
