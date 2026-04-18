import logging
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.domain.enums import CauseCategory

if TYPE_CHECKING:
    from app.integrations.hazard_ai_client import HazardAIClient


logger = logging.getLogger(__name__)

SOURCE_VALUE_CONFIDENCE = 0.95
NO_MATCH_CONFIDENCE = 0.2
AI_FALLBACK_THRESHOLD = 0.65

CAUSE_KEYWORDS: dict[CauseCategory, list[str]] = {
    CauseCategory.WORKPLACE_DESIGN: [
        "layout",
        "workspace",
        "design",
        "access",
        "narrow space",
        "poor visibility",
        "blind spot",
        "workstation design",
        "unsafe design",
    ],
    CauseCategory.HUMAN_FACTORS: [
        "fatigue",
        "inattention",
        "distraction",
        "forgot",
        "mistake",
        "human error",
        "rushed",
        "careless",
        "not paying attention",
    ],
    CauseCategory.ORGANIZATION: [
        "planning",
        "staffing",
        "coordination",
        "management decision",
        "scheduling",
        "workload",
        "understaffed",
        "organization",
    ],
    CauseCategory.HOUSEKEEPING: [
        "clutter",
        "mess",
        "debris",
        "dirty",
        "unclean",
        "spill not cleaned",
        "poor housekeeping",
        "obstruction",
    ],
    CauseCategory.PROCEDURES: [
        "procedure",
        "instruction",
        "sop",
        "work instruction",
        "step was skipped",
        "not followed procedure",
        "missing procedure",
        "incorrect procedure",
    ],
    CauseCategory.MAINTENANCE_MANAGEMENT: [
        "maintenance",
        "inspection overdue",
        "service overdue",
        "not maintained",
        "wear and tear",
        "broken equipment",
        "repair delayed",
        "preventive maintenance",
    ],
    CauseCategory.COMPETENCES: [
        "training",
        "not trained",
        "lack of training",
        "competence",
        "qualification",
        "unfamiliar",
        "inexperienced",
        "did not know",
    ],
    CauseCategory.PPE: [
        "ppe",
        "gloves",
        "helmet",
        "goggles",
        "face shield",
        "safety shoes",
        "protective equipment",
        "no ppe",
        "missing ppe",
    ],
    CauseCategory.COMMUNICATION: [
        "communication",
        "miscommunication",
        "not informed",
        "unclear message",
        "handover",
        "no warning",
        "not communicated",
        "unclear instruction",
    ],
    CauseCategory.PEDESTRIAN: [
        "pedestrian",
        "walking path",
        "walkway",
        "person walking",
        "crossing",
        "foot traffic",
    ],
    CauseCategory.FACILITIES_EQUIPMENT: [
        "facility",
        "equipment failure",
        "broken tool",
        "damaged equipment",
        "faulty equipment",
        "machine issue",
        "infrastructure",
        "building issue",
    ],
}

CAUSE_CLASSIFICATION_SYSTEM_PROMPT = """
You are a safety incident root cause classification system.

Classify the most likely root cause category of the incident into EXACTLY ONE of these categories:
- Workplace Design
- Human Factors
- Organization
- Housekeeping
- Procedures
- Maintenance Management
- Competences
- Personal Protective Equipment
- Communication
- Pedestrian
- Facilities and equipment
- Unknown

Return ONLY valid JSON using this shape:
{"label": "...", "confidence": 0.0, "explanation": "..."}
""".strip()


class ClassificationResult(BaseModel):
    label: CauseCategory
    confidence: float
    explanation: str


class RuleClassificationResult(BaseModel):
    label: CauseCategory
    confidence: float
    explanation: str
    matched_keywords: list[str]


def normalize_source_cause_category(source_cause_category: str | None) -> CauseCategory | None:
    if source_cause_category is None:
        return None
    normalized_value = source_cause_category.strip()
    if not normalized_value:
        return None
    for category in CauseCategory:
        if normalized_value == category.value:
            return category
    return None


def build_source_classification_result(source_category: CauseCategory) -> ClassificationResult:
    return ClassificationResult(
        label=source_category,
        confidence=SOURCE_VALUE_CONFIDENCE,
        explanation="Used valid source cause category.",
    )


class CauseRuleClassifierService:
    def classify_cause_by_rules(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> RuleClassificationResult:
        # Best case: the source system already gave a valid cause category.
        source_category = normalize_source_cause_category(source_cause_category)
        if source_category is not None:
            return RuleClassificationResult(
                label=source_category,
                confidence=SOURCE_VALUE_CONFIDENCE,
                explanation="Used valid source cause category.",
                matched_keywords=[],
            )

        # Fallback: count matching keywords and pick the strongest category.
        text_to_search = f"{text or ''} {source_cause or ''}".lower()
        match_counts: dict[CauseCategory, int] = {}
        matched_keywords_by_category: dict[CauseCategory, list[str]] = {}
        for category, keywords in CAUSE_KEYWORDS.items():
            matched_keywords = []
            for keyword in keywords:
                if self._keyword_matches(text_to_search, keyword):
                    matched_keywords.append(keyword)

            if matched_keywords:
                match_counts[category] = len(matched_keywords)
                matched_keywords_by_category[category] = matched_keywords

        if not match_counts:
            return RuleClassificationResult(
                label=CauseCategory.UNKNOWN,
                confidence=NO_MATCH_CONFIDENCE,
                explanation="No cause keywords matched.",
                matched_keywords=[],
            )

        best_category = max(match_counts, key=match_counts.get)
        best_score = match_counts[best_category]
        if best_score == 1:
            confidence = 0.5
        elif best_score == 2:
            confidence = 0.7
        else:
            confidence = 0.85

        matched_keywords = matched_keywords_by_category[best_category]
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


class AICauseClassifierService:
    def __init__(self, ai_client: "HazardAIClient") -> None:
        self.ai_client = ai_client

    async def classify_cause_ai(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> ClassificationResult | None:
        # Do not spend an AI call when the source category is already valid.
        source_category = normalize_source_cause_category(source_cause_category)
        if source_category is not None:
            return build_source_classification_result(source_category)

        user_prompt = (
            f"Incident text:\n{text}\n\n"
            f"Source cause category:\n{source_cause_category or ''}\n\n"
            f"Source cause:\n{source_cause or ''}"
        )
        try:
            response = await self.ai_client.complete_json(
                system_prompt=CAUSE_CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            logger.info("AI cause data=%s", response.data)
        except Exception:
            return None

        label = response.data.get("label")
        confidence = response.data.get("confidence")
        explanation = response.data.get("explanation")
        if (
            label not in {category.value for category in CauseCategory}
            or not isinstance(confidence, (int, float))
            or not (0.0 <= confidence <= 1.0)
            or not isinstance(explanation, str)
        ):
            return None

        return ClassificationResult(
            label=CauseCategory(label),
            confidence=float(confidence),
            explanation=explanation,
        )


class HybridCauseClassifierService:
    def __init__(self) -> None:
        from app.integrations.hazard_ai_client import HazardAIClient

        self.rule_classifier = CauseRuleClassifierService()
        self.ai_classifier = AICauseClassifierService(HazardAIClient())

    async def classify_cause(
        self,
        text: str,
        source_cause_category: str | None,
        source_cause: str | None,
    ) -> ClassificationResult:
        # Strategy: source value first, AI second, deterministic rules last.
        source_category = normalize_source_cause_category(source_cause_category)
        if source_category is not None:
            return build_source_classification_result(source_category)

        ai_result = await self.ai_classifier.classify_cause_ai(
            text=text,
            source_cause_category=source_cause_category,
            source_cause=source_cause,
        )
        if ai_result is not None and ai_result.confidence >= AI_FALLBACK_THRESHOLD:
            return ai_result

        rule_result = self.rule_classifier.classify_cause_by_rules(
            text=text,
            source_cause_category=source_cause_category,
            source_cause=source_cause,
        )
        return ClassificationResult(
            label=rule_result.label,
            confidence=rule_result.confidence,
            explanation=rule_result.explanation,
        )


__all__ = [
    "AICauseClassifierService",
    "CauseRuleClassifierService",
    "ClassificationResult",
    "HybridCauseClassifierService",
    "RuleClassificationResult",
]
