from app.domain.enums import CauseCategory
from app.services.models.cause_classifier_models import ClassificationResult


SOURCE_VALUE_CONFIDENCE = 0.95


def normalize_source_cause_category(
    source_cause_category: str | None,
) -> CauseCategory | None:
    if source_cause_category is None:
        return None

    normalized_value = source_cause_category.strip()

    if not normalized_value:
        return None

    for category in CauseCategory:
        if normalized_value == category.value:
            return category

    return None


def build_source_classification_result(
    source_category: CauseCategory,
) -> ClassificationResult:
    return ClassificationResult(
        label=source_category,
        confidence=SOURCE_VALUE_CONFIDENCE,
        explanation='Used valid source cause category.',
    )
