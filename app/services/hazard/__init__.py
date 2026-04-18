import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.domain.enums import HazardCategory

if TYPE_CHECKING:
    from app.integrations.hazard_ai_client import HazardAIClient


logger = logging.getLogger(__name__)

NO_MATCH_CONFIDENCE = 0.2
AI_FALLBACK_THRESHOLD = 0.65

HAZARD_KEYWORDS: dict[HazardCategory, list[str]] = {
    HazardCategory.PHYSICAL: [
        "slip",
        "trip",
        "fall",
        "wet floor",
        "working at height",
        "falling object",
        "noise",
        "vibration",
    ],
    HazardCategory.MECHANICAL_EQUIPMENT: [
        "machine",
        "guard",
        "guarding",
        "moving part",
        "pinch",
        "crush",
        "equipment",
        "lockout",
        "tagout",
        "finger",
        "hand injury",
    ],
    HazardCategory.ELECTRICAL: [
        "electric",
        "electrical",
        "shock",
        "wire",
        "wiring",
        "cable",
        "voltage",
        "arc flash",
        "short circuit",
        "faulty equipment",
    ],
    HazardCategory.CHEMICAL: [
        "chemical",
        "spill",
        "leak",
        "fumes",
        "gas",
        "hazardous substance",
        "toxic",
    ],
    HazardCategory.FIRE_EXPLOSION: [
        "fire",
        "explosion",
        "flammable",
        "ignite",
        "combustion",
    ],
    HazardCategory.ERGONOMIC: [
        "lifting",
        "strain",
        "posture",
        "repetitive",
        "ergonomic",
    ],
    HazardCategory.VEHICLE_TRAFFIC: [
        "forklift",
        "vehicle",
        "traffic",
        "collision",
        "pedestrian",
        "reversing",
    ],
    HazardCategory.PROCESS_SAFETY_OPERATIONAL: [
        "process",
        "pressure",
        "valve",
        "overload",
        "system failure",
    ],
    HazardCategory.ENVIRONMENTAL: [
        "environment",
        "pollution",
        "waste",
        "emission",
        "contamination",
    ],
}

HAZARD_CLASSIFICATION_SYSTEM_PROMPT = """
You are a safety classification system.

Classify the incident into ONE allowed hazard category:
- Physical Hazards
- Mechanical / Equipment Hazards
- Electrical Hazards
- Chemical Hazards
- Fire & Explosion Hazards
- Ergonomic Hazards
- Vehicle & Traffic Hazards
- Process Safety / Operational Hazards
- Environmental Hazards
- Unknown

Return ONLY valid JSON using this shape:
{"label": "...", "confidence": 0.0, "explanation": "..."}
""".strip()


class ClassificationResult(BaseModel):
    label: HazardCategory
    confidence: float
    explanation: str


class RuleClassificationResult(BaseModel):
    label: HazardCategory
    confidence: float
    explanation: str
    matched_keywords: list[str]


class HazardRuleClassifierService:
    def classify_hazard_by_rules(
        self,
        text: str,
        activity: str | None,
    ) -> RuleClassificationResult:
        # Count keyword matches for each hazard category and keep the strongest one.
        text_to_search = f"{text or ''} {activity or ''}".lower()
        match_counts: dict[HazardCategory, int] = {}
        matched_keywords_by_category: dict[HazardCategory, list[str]] = {}
        for category, keywords in HAZARD_KEYWORDS.items():
            matched_keywords = []
            for keyword in keywords:
                if keyword in text_to_search:
                    matched_keywords.append(keyword)

            if matched_keywords:
                match_counts[category] = len(matched_keywords)
                matched_keywords_by_category[category] = matched_keywords

        if not match_counts:
            return RuleClassificationResult(
                label=HazardCategory.UNKNOWN,
                confidence=NO_MATCH_CONFIDENCE,
                explanation="No hazard keywords matched.",
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


class AIHazardClassifierService:
    def __init__(self, ai_client: "HazardAIClient") -> None:
        self.ai_client = ai_client

    async def classify_hazard_ai(
        self,
        text: str,
        activity: str | None,
    ) -> ClassificationResult | None:
        user_prompt = f"Incident text:\n{text}\n\nActivity:\n{activity or ''}"
        try:
            response = await self.ai_client.complete_json(
                system_prompt=HAZARD_CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            logger.info("AI hazard data=%s", response.data)
        except Exception:
            return None

        label = response.data.get("label")
        confidence = response.data.get("confidence")
        explanation = response.data.get("explanation")
        if (
            label not in {category.value for category in HazardCategory}
            or not isinstance(confidence, (int, float))
            or not (0.0 <= confidence <= 1.0)
            or not isinstance(explanation, str)
        ):
            return None

        return ClassificationResult(
            label=HazardCategory(label),
            confidence=float(confidence),
            explanation=explanation,
        )


class HybridHazardClassifierService:
    def __init__(self) -> None:
        from app.integrations.hazard_ai_client import HazardAIClient

        self.rule_classifier = HazardRuleClassifierService()
        self.ai_classifier = AIHazardClassifierService(HazardAIClient())

    async def classify_hazard(
        self,
        text: str,
        activity: str | None,
    ) -> ClassificationResult:
        # Strategy: try AI first, but always keep deterministic rules as a fallback.
        ai_result = await self.ai_classifier.classify_hazard_ai(text=text, activity=activity)
        if ai_result is not None and ai_result.confidence >= AI_FALLBACK_THRESHOLD:
            return ai_result

        rule_result = self.rule_classifier.classify_hazard_by_rules(
            text=text,
            activity=activity,
        )
        return ClassificationResult(
            label=rule_result.label,
            confidence=rule_result.confidence,
            explanation=rule_result.explanation,
        )


__all__ = [
    "AIHazardClassifierService",
    "ClassificationResult",
    "HazardRuleClassifierService",
    "HybridHazardClassifierService",
    "RuleClassificationResult",
]
