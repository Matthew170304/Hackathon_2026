from app.domain.enums import RecurrenceFrequency, SeverityLevel
from app.services.risk_scoring_service import RiskScoringService


def test_get_severity_base_score() -> None:
    service = RiskScoringService()

    assert service.get_severity_base_score(SeverityLevel.VERY_LOW) == 1
    assert service.get_severity_base_score(SeverityLevel.LOW) == 5
    assert service.get_severity_base_score(SeverityLevel.MEDIUM) == 10
    assert service.get_severity_base_score(SeverityLevel.HIGH) == 25
    assert service.get_severity_base_score(SeverityLevel.VERY_HIGH) == 75
    assert service.get_severity_base_score(SeverityLevel.UNKNOWN) is None


def test_get_frequency_multiplier() -> None:
    service = RiskScoringService()

    assert service.get_frequency_multiplier(RecurrenceFrequency.LESS_OFTEN) == 1
    assert service.get_frequency_multiplier(RecurrenceFrequency.ONE_TO_FIVE_YEARS) == 2
    assert service.get_frequency_multiplier(RecurrenceFrequency.SIX_MONTHS_TO_ONE_YEAR) == 3
    assert service.get_frequency_multiplier(RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS) == 4
    assert service.get_frequency_multiplier(RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS) == 5
    assert service.get_frequency_multiplier(RecurrenceFrequency.UNKNOWN) is None


def test_calculate_risk_score_high_frequency() -> None:
    service = RiskScoringService()

    assert service.calculate_risk_score(
        SeverityLevel.HIGH,
        RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS,
    ) == 125


def test_calculate_risk_score_medium_frequency() -> None:
    service = RiskScoringService()

    assert service.calculate_risk_score(
        SeverityLevel.MEDIUM,
        RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS,
    ) == 40


def test_calculate_risk_score_unknown_severity() -> None:
    service = RiskScoringService()

    assert service.calculate_risk_score(
        SeverityLevel.UNKNOWN,
        RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS,
    ) is None


def test_calculate_risk_score_unknown_frequency() -> None:
    service = RiskScoringService()

    assert service.calculate_risk_score(
        SeverityLevel.HIGH,
        RecurrenceFrequency.UNKNOWN,
    ) is None


def test_get_risk_level_label() -> None:
    service = RiskScoringService()

    assert service.get_risk_level_label(None) == 'Unknown'
    assert service.get_risk_level_label(10) == 'Low'
    assert service.get_risk_level_label(40) == 'Medium'
    assert service.get_risk_level_label(100) == 'High'
    assert service.get_risk_level_label(101) == 'Critical'
