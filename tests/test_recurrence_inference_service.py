import asyncio

from app.domain.enums import RecurrenceFrequency
from app.services.recurrence_inference import (
    RecurrenceInferenceService,
    RecurrenceRuleInferenceService,
)


def test_rule_inference_zero_to_fourteen_days() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='This happens daily near the production entry.',
        location=None,
        activity=None,
    )

    assert result.recurrence_frequency == RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS


def test_rule_inference_fourteen_days_to_six_months() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='This is a repeated temporary issue.',
        location=None,
        activity=None,
    )

    assert result.recurrence_frequency == RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS


def test_rule_inference_six_months_to_one_year() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='The issue happens about twice a year.',
        location=None,
        activity=None,
    )

    assert result.recurrence_frequency == RecurrenceFrequency.SIX_MONTHS_TO_ONE_YEAR


def test_rule_inference_one_to_five_years() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='This is checked during the annual maintenance cycle.',
        location=None,
        activity=None,
    )

    assert result.recurrence_frequency == RecurrenceFrequency.ONE_TO_FIVE_YEARS


def test_rule_inference_less_often() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='This was an isolated one-off event.',
        location=None,
        activity=None,
    )

    assert result.recurrence_frequency == RecurrenceFrequency.LESS_OFTEN


def test_rule_inference_unknown_recurrence() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='General observation was submitted.',
        location=None,
        activity=None,
    )

    assert result.recurrence_frequency == RecurrenceFrequency.UNKNOWN


def test_infer_recurrence_uses_valid_source_value() -> None:
    service = RecurrenceInferenceService()

    result = asyncio.run(
        service.infer_recurrence(
            text='General observation.',
            source_recurrence='0 - 14 days',
            location=None,
            activity=None,
        )
    )

    assert result.recurrence_frequency == RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS
    assert result.confidence == 0.95
    assert result.used_source_value is True


def test_infer_recurrence_falls_back_when_source_value_is_unknown() -> None:
    service = RecurrenceInferenceService()

    result = asyncio.run(
        service.infer_recurrence(
            text='This happens daily near the production entry.',
            source_recurrence='Unknown',
            location=None,
            activity=None,
        )
    )

    assert result.recurrence_frequency == RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS
    assert result.used_source_value is False


def test_rule_inference_uses_location_and_activity_text() -> None:
    service = RecurrenceRuleInferenceService()

    result = service.infer_recurrence_by_rules(
        text='General observation was submitted.',
        location='Nordborg recurring walkway issue',
        activity='Temporary barrier is installed monthly.',
    )

    assert result.recurrence_frequency == RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS
