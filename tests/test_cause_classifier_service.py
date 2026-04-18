import pytest

from app.domain.enums import CauseCategory
from app.services.cause_classifier_service import (
    AICauseClassifierService,
    CauseRuleClassifierService,
    HybridCauseClassifierService,
)
from app.integrations.hazard_ai_client import HazardAIClient


def test_rule_classifier_uses_valid_source_cause_category() -> None:
    classifier = CauseRuleClassifierService()

    result = classifier.classify_cause_by_rules(
        text="Some unrelated text.",
        source_cause_category="Procedures",
        source_cause="",
    )

    assert result.label == CauseCategory.PROCEDURES
    assert result.confidence == 0.95


def test_rule_classifier_housekeeping() -> None:
    classifier = CauseRuleClassifierService()

    result = classifier.classify_cause_by_rules(
        text="The worker slipped because clutter and debris blocked the walkway.",
        source_cause_category=None,
        source_cause=None,
    )

    assert result.label == CauseCategory.HOUSEKEEPING


def test_rule_classifier_competences() -> None:
    classifier = CauseRuleClassifierService()

    result = classifier.classify_cause_by_rules(
        text="The operator was not trained and did not know the correct setup.",
        source_cause_category=None,
        source_cause=None,
    )

    assert result.label == CauseCategory.COMPETENCES


def test_rule_classifier_ppe() -> None:
    classifier = CauseRuleClassifierService()

    result = classifier.classify_cause_by_rules(
        text="The employee handled the material with no gloves and missing PPE.",
        source_cause_category=None,
        source_cause=None,
    )

    assert result.label == CauseCategory.PPE


@pytest.mark.asyncio
async def test_ai_cause_classifier_real_api_procedures() -> None:
    classifier = AICauseClassifierService(ai_client=HazardAIClient())

    result = await classifier.classify_cause_ai(
        text="The task was performed without following the required work instruction and the procedure step was skipped.",
        source_cause_category=None,
        source_cause=None,
    )

    assert result is not None
    assert result.label == CauseCategory.PROCEDURES
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.explanation, str)
    assert result.explanation.strip() != ""


@pytest.mark.asyncio
async def test_hybrid_cause_classifier_real_api_human_factors() -> None:
    classifier = HybridCauseClassifierService()

    result = await classifier.classify_cause(
        text="The worker was distracted, rushed, and not paying attention during the task.",
        source_cause_category=None,
        source_cause=None,
    )

    assert result.label == CauseCategory.HUMAN_FACTORS
    assert 0.0 <= result.confidence <= 1.0