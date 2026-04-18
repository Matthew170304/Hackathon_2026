from app.domain.enums import CauseCategory, HazardCategory, RecurrenceFrequency, SeverityLevel
from app.schemas.incident_schemas import IncidentCreateRequest
from app.schemas.processing_schemas import ProcessingResult
from app.services.cause import HybridCauseClassifierService
from app.services.hazard import HybridHazardClassifierService
from app.services.language import LanguageService
from app.services.recommendation import RecommendationService
from app.services.recurrence_inference import RecurrenceInferenceService
from app.services.risk_scoring import RiskScoringService
from app.services.severity_inference import SeverityInferenceService
from app.services.text_cleaning import TextCleaningService
from app.services.translation import TranslationService


class IncidentProcessingService:
    def __init__(self) -> None:
        self.text_cleaning = TextCleaningService()
        self.language = LanguageService()
        self.translation = TranslationService()
        self.hazard_classifier = HybridHazardClassifierService()
        self.cause_classifier = HybridCauseClassifierService()
        self.severity_inference = SeverityInferenceService()
        self.recurrence_inference = RecurrenceInferenceService()
        self.risk_scoring = RiskScoringService()
        self.recommendations = RecommendationService()

    async def process_incident(self, incident: IncidentCreateRequest) -> ProcessingResult:
        # Step 1: Prepare the text that every later service will analyze.
        cleaned_text = self.text_cleaning.build_analysis_text(incident)

        # Step 2: Translate only when the source text appears to be non-English.
        original_language = self.language.detect_language(cleaned_text)
        should_translate = self.language.should_translate(original_language)
        translation_language = original_language if should_translate else None
        translated_title, translated_description = await self.translation.translate_incident_fields(
            incident,
            source_language=translation_language,
        )

        # Step 3: Give classifiers both original context and English translation.
        analysis_text = self._build_classifier_text(
            cleaned_text=cleaned_text,
            translated_title=translated_title,
            translated_description=translated_description,
        )

        # Step 4: Enrich the incident with safety intelligence.
        hazard_result = await self.hazard_classifier.classify_hazard(
            text=analysis_text,
            activity=incident.activity,
        )
        cause_result = await self.cause_classifier.classify_cause(
            text=analysis_text,
            source_cause_category=incident.cause_category,
            source_cause=incident.cause,
        )
        severity_result = await self.severity_inference.infer_severity(
            text=analysis_text,
            source_severity=incident.severity_level,
            hazard_category=hazard_result.label,
        )
        recurrence_result = await self.recurrence_inference.infer_recurrence(
            text=analysis_text,
            source_recurrence=incident.recurrence_frequency,
            location=incident.location,
            activity=incident.activity,
        )

        # Step 5: Convert severity and recurrence into the Danfoss risk score.
        risk_score = self.risk_scoring.calculate_risk_score(
            severity_result.severity_level,
            recurrence_result.recurrence_frequency,
        )
        risk_label = self.risk_scoring.get_risk_level_label(risk_score)

        # Step 6: Create one action recommendation for this incident.
        recommendation = self.recommendations.generate_incident_recommendation(
            hazard_category=hazard_result.label,
            cause_category=cause_result.label,
            risk_score=risk_score,
        )

        return ProcessingResult(
            cleaned_text=cleaned_text,
            original_language=original_language,
            translated_title=translated_title,
            translated_description=translated_description,
            hazard_category=hazard_result.label,
            hazard_confidence=hazard_result.confidence,
            hazard_explanation=hazard_result.explanation,
            cause_category=cause_result.label,
            cause_confidence=cause_result.confidence,
            cause_explanation=cause_result.explanation,
            severity_level=severity_result.severity_level,
            severity_confidence=severity_result.confidence,
            severity_explanation=severity_result.explanation,
            recurrence_frequency=recurrence_result.recurrence_frequency,
            recurrence_confidence=recurrence_result.confidence,
            recurrence_explanation=recurrence_result.explanation,
            risk_score=risk_score,
            risk_level_label=risk_label,
            recommendation_summary=recommendation.summary,
            needs_human_review=self.should_require_human_review(
                hazard_result.label,
                cause_result.label,
                severity_result.severity_level,
                recurrence_result.recurrence_frequency,
                hazard_result.confidence,
                cause_result.confidence,
                severity_result.confidence,
                recurrence_result.confidence,
                risk_score,
            ),
        )

    @staticmethod
    def should_require_human_review(
        hazard_category: HazardCategory,
        cause_category: CauseCategory,
        severity_level: SeverityLevel,
        recurrence_frequency: RecurrenceFrequency,
        hazard_confidence: float,
        cause_confidence: float,
        severity_confidence: float,
        recurrence_confidence: float,
        risk_score: int | None,
    ) -> bool:
        if risk_score is not None and risk_score > 100:
            return True
        if HazardCategory.UNKNOWN == hazard_category or CauseCategory.UNKNOWN == cause_category:
            return True
        if SeverityLevel.UNKNOWN == severity_level or RecurrenceFrequency.UNKNOWN == recurrence_frequency:
            return True
        return min(
            hazard_confidence,
            cause_confidence,
            severity_confidence,
            recurrence_confidence,
        ) < 0.55

    @staticmethod
    def _build_classifier_text(
        cleaned_text: str,
        translated_title: str | None,
        translated_description: str | None,
    ) -> str:
        translated_lines = []
        if translated_title:
            translated_lines.append(f"Title: {translated_title}")
        if translated_description:
            translated_lines.append(f"Description: {translated_description}")

        if translated_lines:
            return (
                "Original incident:\n"
                f"{cleaned_text}\n\n"
                "English translation:\n"
                f"{chr(10).join(translated_lines)}"
            )

        return cleaned_text
