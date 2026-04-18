import asyncio

from app.domain.enums import HazardCategory, SeverityLevel
from app.services.severity_inference_service import (
    SeverityInferenceService,
    SeverityRuleInferenceService,
)


def test_rule_inference_low_severity() -> None:
    service = SeverityRuleInferenceService()

    result = service.infer_severity_by_rules(
        text='Employee reported a minor near miss with no injury.',
        hazard_category=HazardCategory.PHYSICAL,
    )

    assert result.severity_level == SeverityLevel.LOW
    assert result.used_source_value is False


def test_rule_inference_medium_severity() -> None:
    service = SeverityRuleInferenceService()

    result = service.infer_severity_by_rules(
        text='Operator had a slip and fall near the production line.',
        hazard_category=HazardCategory.PHYSICAL,
    )

    assert result.severity_level == SeverityLevel.MEDIUM


def test_rule_inference_high_severity() -> None:
    service = SeverityRuleInferenceService()

    result = service.infer_severity_by_rules(
        text='Worker was exposed to an unguarded moving machine part.',
        hazard_category=HazardCategory.MECHANICAL_EQUIPMENT,
    )

    assert result.severity_level == SeverityLevel.HIGH


def test_rule_inference_very_high_severity() -> None:
    service = SeverityRuleInferenceService()

    result = service.infer_severity_by_rules(
        text='There was a fatal structural collapse risk.',
        hazard_category=HazardCategory.PROCESS_SAFETY_OPERATIONAL,
    )

    assert result.severity_level == SeverityLevel.VERY_HIGH


def test_rule_inference_unknown_severity() -> None:
    service = SeverityRuleInferenceService()

    result = service.infer_severity_by_rules(
        text='General observation was submitted.',
        hazard_category=HazardCategory.UNKNOWN,
    )

    assert result.severity_level == SeverityLevel.UNKNOWN


def test_infer_severity_uses_valid_source_value() -> None:
    service = SeverityInferenceService()

    result = asyncio.run(
        service.infer_severity(
            text='General observation.',
            source_severity='High',
            hazard_category=HazardCategory.UNKNOWN,
        )
    )

    assert result.severity_level == SeverityLevel.HIGH
    assert result.confidence == 0.95
    assert result.used_source_value is True


def test_infer_severity_falls_back_when_source_value_is_unknown() -> None:
    service = SeverityInferenceService()

    result = asyncio.run(
        service.infer_severity(
            text='Worker was exposed to an unguarded moving machine part.',
            source_severity='Unknown',
            hazard_category=HazardCategory.MECHANICAL_EQUIPMENT,
        )
    )

    assert result.severity_level == SeverityLevel.HIGH
    assert result.used_source_value is False


def test_rule_inference_uses_high_potential_hazard_category() -> None:
    service = SeverityRuleInferenceService()

    result = service.infer_severity_by_rules(
        text='General observation was submitted.',
        hazard_category=HazardCategory.ELECTRICAL,
    )

    assert result.severity_level == SeverityLevel.HIGH
    assert result.confidence == 0.65
