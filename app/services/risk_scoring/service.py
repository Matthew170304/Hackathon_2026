from app.domain.enums import RecurrenceFrequency, SeverityLevel


LOW_RISK_MAX_SCORE = 10
MEDIUM_RISK_MAX_SCORE = 40
HIGH_RISK_MAX_SCORE = 100

RISK_LABEL_UNKNOWN = "Unknown"
RISK_LABEL_LOW = "Low"
RISK_LABEL_MEDIUM = "Medium"
RISK_LABEL_HIGH = "High"
RISK_LABEL_CRITICAL = "Critical"


class RiskScoringService:
    SEVERITY_BASE_SCORES = {
        SeverityLevel.VERY_LOW: 1,
        SeverityLevel.LOW: 5,
        SeverityLevel.MEDIUM: 10,
        SeverityLevel.HIGH: 25,
        SeverityLevel.VERY_HIGH: 75,
    }
    FREQUENCY_MULTIPLIERS = {
        RecurrenceFrequency.LESS_OFTEN: 1,
        RecurrenceFrequency.ONE_TO_FIVE_YEARS: 2,
        RecurrenceFrequency.SIX_MONTHS_TO_ONE_YEAR: 3,
        RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS: 4,
        RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS: 5,
    }

    def get_severity_base_score(self, severity: SeverityLevel) -> int | None:
        return self.SEVERITY_BASE_SCORES.get(severity)

    def get_frequency_multiplier(self, frequency: RecurrenceFrequency) -> int | None:
        return self.FREQUENCY_MULTIPLIERS.get(frequency)

    def calculate_risk_score(
        self,
        severity: SeverityLevel,
        frequency: RecurrenceFrequency,
    ) -> int | None:
        severity_base_score = self.get_severity_base_score(severity)
        frequency_multiplier = self.get_frequency_multiplier(frequency)

        if severity_base_score is None or frequency_multiplier is None:
            return None

        return severity_base_score * frequency_multiplier

    def get_risk_level_label(self, risk_score: int | None) -> str:
        if risk_score is None:
            return RISK_LABEL_UNKNOWN
        if risk_score <= LOW_RISK_MAX_SCORE:
            return RISK_LABEL_LOW
        if risk_score <= MEDIUM_RISK_MAX_SCORE:
            return RISK_LABEL_MEDIUM
        if risk_score <= HIGH_RISK_MAX_SCORE:
            return RISK_LABEL_HIGH

        return RISK_LABEL_CRITICAL
