from app.domain.enums import HazardCategory, SeverityLevel
from app.services.models.inference_models import SeverityInferenceResult


SOURCE_VALUE_CONFIDENCE = 0.95
RULE_CONFIDENCE = 0.75
UNKNOWN_CONFIDENCE = 0.2
HIGH_POTENTIAL_HAZARD_CONFIDENCE = 0.65


VERY_HIGH_KEYWORDS = (
    "fatal",
    "death",
    "life threatening",
    "structural collapse",
    "collapse risk",
)
HIGH_KEYWORDS = (
    "unguarded",
    "moving machine",
    "moving part",
    "amputation",
    "permanent",
    "crush",
    "electrical shock",
    "arc flash",
)
MEDIUM_KEYWORDS = (
    "slip",
    "trip",
    "fall",
    "fracture",
    "lost time",
    "medical treatment",
)
LOW_KEYWORDS = (
    "minor",
    "near miss",
    "no injury",
    "first aid",
    "local aches",
)


def _normalize_source_severity(source_severity: str | None) -> SeverityLevel | None:
    if source_severity is None:
        return None

    normalized_value = source_severity.strip()
    if not normalized_value:
        return None

    for severity in SeverityLevel:
        if normalized_value.lower() == severity.value.lower():
            return severity

    return None


class SeverityRuleInferenceService:
    def infer_severity_by_rules(
        self,
        text: str,
        hazard_category: HazardCategory,
    ) -> SeverityInferenceResult:
        normalized_text = (text or "").lower()

        if any(keyword in normalized_text for keyword in VERY_HIGH_KEYWORDS):
            return self._result(SeverityLevel.VERY_HIGH, "Matched very high severity keywords.")

        if any(keyword in normalized_text for keyword in HIGH_KEYWORDS):
            return self._result(SeverityLevel.HIGH, "Matched high severity keywords.")

        if any(keyword in normalized_text for keyword in MEDIUM_KEYWORDS):
            return self._result(SeverityLevel.MEDIUM, "Matched medium severity keywords.")

        if any(keyword in normalized_text for keyword in LOW_KEYWORDS):
            return self._result(SeverityLevel.LOW, "Matched low severity keywords.")

        if hazard_category in {
            HazardCategory.ELECTRICAL,
            HazardCategory.FIRE_EXPLOSION,
            HazardCategory.PROCESS_SAFETY_OPERATIONAL,
        }:
            return self._result(
                SeverityLevel.HIGH,
                "Hazard category has high potential severity.",
                confidence=HIGH_POTENTIAL_HAZARD_CONFIDENCE,
            )

        return SeverityInferenceResult(
            severity_level=SeverityLevel.UNKNOWN,
            confidence=UNKNOWN_CONFIDENCE,
            explanation="No severity indicators matched.",
            used_source_value=False,
        )

    @staticmethod
    def _result(
        severity_level: SeverityLevel,
        explanation: str,
        confidence: float = RULE_CONFIDENCE,
    ) -> SeverityInferenceResult:
        return SeverityInferenceResult(
            severity_level=severity_level,
            confidence=confidence,
            explanation=explanation,
            used_source_value=False,
        )


class SeverityInferenceService:
    def __init__(self) -> None:
        self.rule_inference = SeverityRuleInferenceService()

    async def infer_severity(
        self,
        text: str,
        source_severity: str | None,
        hazard_category: HazardCategory,
    ) -> SeverityInferenceResult:
        source_value = _normalize_source_severity(source_severity)

        if source_value is not None and source_value != SeverityLevel.UNKNOWN:
            return SeverityInferenceResult(
                severity_level=source_value,
                confidence=SOURCE_VALUE_CONFIDENCE,
                explanation="Used valid source severity.",
                used_source_value=True,
            )

        return self.rule_inference.infer_severity_by_rules(
            text=text,
            hazard_category=hazard_category,
        )
