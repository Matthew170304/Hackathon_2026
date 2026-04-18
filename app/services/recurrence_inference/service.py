from app.domain.enums import RecurrenceFrequency
from app.services.models.inference_models import RecurrenceInferenceResult


SOURCE_VALUE_CONFIDENCE = 0.95
RULE_CONFIDENCE = 0.75
UNKNOWN_CONFIDENCE = 0.2


ZERO_TO_FOURTEEN_DAYS_KEYWORDS = (
    "daily",
    "every day",
    "weekly",
    "often",
    "frequent",
)
FOURTEEN_DAYS_TO_SIX_MONTHS_KEYWORDS = (
    "repeated",
    "temporary",
    "monthly",
    "recurring",
)
SIX_MONTHS_TO_ONE_YEAR_KEYWORDS = (
    "twice a year",
    "several times a year",
    "half yearly",
)
ONE_TO_FIVE_YEARS_KEYWORDS = (
    "annual",
    "yearly",
    "maintenance cycle",
)
LESS_OFTEN_KEYWORDS = (
    "isolated",
    "one-off",
    "rare",
    "exceptional",
)


def _normalize_source_recurrence(
    source_recurrence: str | None,
) -> RecurrenceFrequency | None:
    if source_recurrence is None:
        return None

    normalized_value = source_recurrence.strip()
    if not normalized_value:
        return None

    for recurrence in RecurrenceFrequency:
        if normalized_value.lower() == recurrence.value.lower():
            return recurrence

    return None


class RecurrenceRuleInferenceService:
    def infer_recurrence_by_rules(
        self,
        text: str,
        location: str | None,
        activity: str | None,
    ) -> RecurrenceInferenceResult:
        combined = f"{text or ''} {location or ''} {activity or ''}".lower()

        if any(keyword in combined for keyword in ZERO_TO_FOURTEEN_DAYS_KEYWORDS):
            return self._result(
                RecurrenceFrequency.ZERO_TO_FOURTEEN_DAYS,
                "Matched frequent recurrence keywords.",
            )

        if any(keyword in combined for keyword in FOURTEEN_DAYS_TO_SIX_MONTHS_KEYWORDS):
            return self._result(
                RecurrenceFrequency.FOURTEEN_DAYS_TO_SIX_MONTHS,
                "Matched repeated issue keywords.",
            )

        if any(keyword in combined for keyword in SIX_MONTHS_TO_ONE_YEAR_KEYWORDS):
            return self._result(
                RecurrenceFrequency.SIX_MONTHS_TO_ONE_YEAR,
                "Matched semiannual recurrence keywords.",
            )

        if any(keyword in combined for keyword in ONE_TO_FIVE_YEARS_KEYWORDS):
            return self._result(
                RecurrenceFrequency.ONE_TO_FIVE_YEARS,
                "Matched annual recurrence keywords.",
            )

        if any(keyword in combined for keyword in LESS_OFTEN_KEYWORDS):
            return self._result(
                RecurrenceFrequency.LESS_OFTEN,
                "Matched rare event keywords.",
            )

        return RecurrenceInferenceResult(
            recurrence_frequency=RecurrenceFrequency.UNKNOWN,
            confidence=UNKNOWN_CONFIDENCE,
            explanation="No recurrence indicators matched.",
            used_source_value=False,
        )

    @staticmethod
    def _result(
        recurrence_frequency: RecurrenceFrequency,
        explanation: str,
    ) -> RecurrenceInferenceResult:
        return RecurrenceInferenceResult(
            recurrence_frequency=recurrence_frequency,
            confidence=RULE_CONFIDENCE,
            explanation=explanation,
            used_source_value=False,
        )


class RecurrenceInferenceService:
    def __init__(self) -> None:
        self.rule_inference = RecurrenceRuleInferenceService()

    async def infer_recurrence(
        self,
        text: str,
        source_recurrence: str | None,
        location: str | None,
        activity: str | None,
    ) -> RecurrenceInferenceResult:
        source_value = _normalize_source_recurrence(source_recurrence)

        if source_value is not None and source_value != RecurrenceFrequency.UNKNOWN:
            return RecurrenceInferenceResult(
                recurrence_frequency=source_value,
                confidence=SOURCE_VALUE_CONFIDENCE,
                explanation="Used valid source recurrence frequency.",
                used_source_value=True,
            )

        return self.rule_inference.infer_recurrence_by_rules(
            text=text,
            location=location,
            activity=activity,
        )
