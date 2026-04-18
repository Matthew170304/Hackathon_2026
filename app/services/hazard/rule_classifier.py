from app.domain.enums import HazardCategory
from app.services.hazard.keywords import HAZARD_KEYWORDS
from app.services.hazard.models import RuleClassificationResult


NO_MATCH_CONFIDENCE = 0.2

LOW_CONFIDENCE_THRESHOLD = 1
MEDIUM_CONFIDENCE_THRESHOLD = 2

LOW_CONFIDENCE_SCORE = 0.5
MEDIUM_CONFIDENCE_SCORE = 0.7
HIGH_CONFIDENCE_SCORE = 0.85


class HazardRuleClassifierService:
    def classify_hazard_by_rules(
        self,
        text: str,
        activity: str | None,
    ) -> RuleClassificationResult:
        combined = f"{text or ''} {activity or ''}".lower()

        scores: dict[HazardCategory, int] = {}
        matches: dict[HazardCategory, list[str]] = {}

        for category, keywords in HAZARD_KEYWORDS.items():
            matched_keywords = [keyword for keyword in keywords if keyword in combined]

            if matched_keywords:
                scores[category] = len(matched_keywords)
                matches[category] = matched_keywords

        if not scores:
            return RuleClassificationResult(
                label=HazardCategory.UNKNOWN,
                confidence=NO_MATCH_CONFIDENCE,
                explanation='No hazard keywords matched.',
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
