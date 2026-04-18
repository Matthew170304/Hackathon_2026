from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Incident, ProcessedIncident, utc_now
from app.domain.enums import HazardCategory, ProcessingStatus
from app.schemas.incident_schemas import IncidentCreateRequest
from app.schemas.processing_schemas import ProcessingResult


class IncidentRepository:
    """
    Repository for raw and processed incident persistence.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_raw_incident(
        self,
        incident: IncidentCreateRequest,
        source: str,
        source_batch_id: UUID | str | None = None,
    ) -> Incident:
        """
        Save raw incident input to the database.

        Args:
            incident: validated incident request
            source: "api" or "excel"
            source_batch_id: batch id when incident comes from Excel

        Returns:
            Persisted Incident database model.
        """
        country, site = self._extract_country_and_site(incident.location)

        db_incident = Incident(
            external_case_id=incident.external_case_id,
            source=source,
            source_batch_id=str(source_batch_id) if source_batch_id is not None else None,
            case_type=incident.case_type,
            location=incident.location,
            country=country,
            site=site,
            responsible_entity=incident.responsible_entity,
            occurred_at=incident.occurred_at,
            title=incident.title,
            description=incident.description,
            activity=incident.activity,
            severity_level_source=incident.severity_level,
            recurrence_frequency_source=incident.recurrence_frequency,
            classification_source=incident.classification,
            cause_category_source=incident.cause_category,
            cause_source=incident.cause,
            immediate_actions=incident.immediate_actions,
            action_description=incident.action_description,
            validation_description=incident.validation_description,
        )

        self.session.add(db_incident)
        self.session.commit()
        self.session.refresh(db_incident)

        return db_incident

    def save_processing_result(
        self,
        incident_id: UUID | str,
        result: ProcessingResult,
    ) -> ProcessedIncident:
        """
        Save processed AI/risk output for an incident.

        Args:
            incident_id: raw incident id
            result: complete processing result

        Returns:
            Persisted ProcessedIncident database model.
        """
        db_processed = ProcessedIncident(
            incident_id=str(incident_id),
            processing_status=(
                ProcessingStatus.NEEDS_REVIEW.value
                if result.needs_human_review
                else ProcessingStatus.PROCESSED.value
            ),
            original_language=result.original_language,
            cleaned_text=result.cleaned_text,
            translated_title=result.translated_title,
            translated_description=result.translated_description,
            hazard_category=self._value(result.hazard_category),
            hazard_confidence=result.hazard_confidence,
            hazard_explanation=result.hazard_explanation,
            cause_category=self._value(result.cause_category),
            cause_confidence=result.cause_confidence,
            cause_explanation=result.cause_explanation,
            severity_level=self._value(result.severity_level),
            severity_confidence=result.severity_confidence,
            severity_explanation=result.severity_explanation,
            recurrence_frequency=self._value(result.recurrence_frequency),
            recurrence_confidence=result.recurrence_confidence,
            recurrence_explanation=result.recurrence_explanation,
            risk_score=result.risk_score,
            risk_level_label=result.risk_level_label,
            recommendation_summary=result.recommendation_summary,
            needs_human_review=result.needs_human_review,
            processed_at=utc_now(),
        )

        self.session.add(db_processed)
        self.session.commit()
        self.session.refresh(db_processed)

        return db_processed

    def get_processed_incident(self, incident_id: UUID | str) -> ProcessedIncident | None:
        """
        Fetch processed incident by raw incident id.

        Returns:
            ProcessedIncident if found, otherwise None.
        """
        statement = (
            select(ProcessedIncident)
            .options(joinedload(ProcessedIncident.incident))
            .where(ProcessedIncident.incident_id == str(incident_id))
        )

        return self.session.scalar(statement)

    def list_processed_incidents(
        self,
        year: int | None = None,
        location: str | None = None,
        hazard_category: HazardCategory | None = None,
        min_risk_score: int | None = None,
    ) -> list[ProcessedIncident]:
        """
        List processed incidents with optional filters for analytics and Power BI output.

        Returns:
            List of ProcessedIncident database models.
        """
        statement = (
            select(ProcessedIncident)
            .join(ProcessedIncident.incident)
            .options(joinedload(ProcessedIncident.incident))
        )

        if year is not None:
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
            statement = statement.where(Incident.occurred_at >= start, Incident.occurred_at < end)

        if location is not None:
            statement = statement.where(Incident.location == location)

        if hazard_category is not None:
            statement = statement.where(ProcessedIncident.hazard_category == hazard_category.value)

        if min_risk_score is not None:
            statement = statement.where(ProcessedIncident.risk_score >= min_risk_score)

        return list(self.session.scalars(statement).all())

    @staticmethod
    def _extract_country_and_site(location: str | None) -> tuple[str | None, str | None]:
        if not location:
            return None, None

        parts = [part.strip() for part in location.split(" - ") if part.strip()]
        country = parts[0] if len(parts) >= 1 else None
        site = parts[1] if len(parts) >= 2 else None

        return country, site

    @staticmethod
    def _value(value: object) -> str:
        return getattr(value, "value", value)  # type: ignore[return-value]
