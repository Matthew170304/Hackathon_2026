import re

from app.domain.enums import CauseCategory
from app.services.cause.source_values import (
    SOURCE_VALUE_CONFIDENCE,
    normalize_source_cause_category,
)
from app.services.cause.keywords import CAUSE_KEYWORDS
from app.services.models.cause_classifier_models import RuleClassificationResult


NO_MATCH_CONFIDENCE = 0.2

LOW_CONFIDENCE_THRESHOLD = 1
MEDIUM_CONFIDENCE_THRESHOLD = 2

LOW_CONFIDENCE_SCORE = 0.5
MEDIUM_CONFIDENCE_SCORE = 0.7
HIGH_CONFIDENCE_SCORE = 0.85


class CauseRuleClassifierService:
    def classify_cause_by_rules(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> RuleClassificationResult:
        source_category = normalize_source_cause_category(source_cause_category)

        if source_category is not None:
            return RuleClassificationResult(
                label=source_category,
                confidence=SOURCE_VALUE_CONFIDENCE,
                explanation='Used valid source cause category.',
                matched_keywords=[],
            )

        combined = f"{text or ''} {source_cause or ''}".lower()

        scores: dict[CauseCategory, int] = {}
        matches: dict[CauseCategory, list[str]] = {}

        for category, keywords in CAUSE_KEYWORDS.items():
            matched_keywords = [
                keyword for keyword in keywords if self._keyword_matches(combined, keyword)
            ]

            if matched_keywords:
                scores[category] = len(matched_keywords)
                matches[category] = matched_keywords

        if not scores:
            return RuleClassificationResult(
                label=CauseCategory.UNKNOWN,
                confidence=NO_MATCH_CONFIDENCE,
                explanation='No cause keywords matched.',
                matched_keywords=[],
            )

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        matched_keywords = matches[best_category]

        if best_score == LOW_CONFIDENCE_THRESHOLD:
            confidence = LOW_CONFIDENCE_SCORE
        elif best_score == MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = MEDIUM_CONFIDENCE_SCORE
        else:
            confidence = HIGH_CONFIDENCE_SCORE

        return RuleClassificationResult(
            label=best_category,
            confidence=confidence,
            explanation=f"Matched keywords: {', '.join(matched_keywords)}",
            matched_keywords=matched_keywords,
        )

    @staticmethod
    def _keyword_matches(text: str, keyword: str) -> bool:
        if len(keyword) <= 3 or " " not in keyword:
            return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
        return keyword in text
