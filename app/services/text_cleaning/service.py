import re

from app.schemas.incident_schemas import IncidentCreateRequest


class TextCleaningService:
    EMPTY_VALUES_PLACEHOLDERS = {
        "",
        "-- not selected --",
        "-- not selected on this level --",
        "-no value-",
        "n/a",
        "na",
        "no value",
        "none",
        "null",
    }
    FIELDS = [
        ("Title", "title"),
        ("Description", "description"),
        ("Location", "location"),
        ("Immediate actions", "immediate_actions"),
        ("Action description", "action_description"),
        ("Validation description", "validation_description"),
    ]

    def clean_text(self, text: str | None) -> str:
        if text is None:
            return ""

        cleaned = str(text).strip()
        if cleaned.lower() in self.EMPTY_VALUES_PLACEHOLDERS:
            return ""

        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s*-\s*", " - ", cleaned)

        return cleaned.strip()

    def build_analysis_text(self, incident: IncidentCreateRequest) -> str:
        analysis_text = []
        for label, field_name in self.FIELDS:
            value = getattr(incident, field_name, None)
            cleaned_value = self.clean_text(value)

            if cleaned_value:
                analysis_text.append(f"{label}: {cleaned_value}")

        return " | ".join(analysis_text)

    @staticmethod
    def extract_country_and_site(location: str | None) -> tuple[str | None, str | None]:
        if location is None:
            return None, None

        cleaned_location = TextCleaningService().clean_text(location)
        if not cleaned_location:
            return None, None

        parts = [part.strip() for part in cleaned_location.split("-") if part.strip()]
        country = parts[0] if len(parts) > 0 else None
        site = parts[1] if len(parts) > 1 else None

        return country, site
