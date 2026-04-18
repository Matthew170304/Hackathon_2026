from __future__ import annotations

import inspect
from typing import Optional, Protocol, Tuple, runtime_checkable

from app.schemas.incident_schemas import IncidentCreateRequest


TRANSLATABLE_LANGUAGE_CODES = {
    "da",
    "pl",
    "sl",
    "zh",
    "de",
    "nl",
    "bg",
    "ro",
    "es",
    "pt",
}


@runtime_checkable
class TranslatorClient(Protocol):
    async def translate_to_english(
        self,
        text: str,
        source_language: str | None = None,
    ) -> str:
        ...


class TranslationService:
    def __init__(self, translator_client: TranslatorClient | None = None) -> None:
        if translator_client is None:
            try:
                from app.integrations.translator_client import build_translator_client

                translator_client = build_translator_client()
            except Exception:
                translator_client = None

        self._translator = translator_client

    async def translate_to_english(
        self,
        text: str,
        source_language: Optional[str] = None,
    ) -> str:
        if not text or not text.strip():
            return ""

        if (
            source_language is None
            or source_language == "en"
            or source_language not in TRANSLATABLE_LANGUAGE_CODES
        ):
            return text

        return await self._translate_with_client(text, source_language)

    async def translate_incident_fields(
        self,
        incident: IncidentCreateRequest,
        source_language: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        translated_title = (
            await self.translate_to_english(incident.title, source_language=source_language)
            if incident.title is not None
            else None
        )

        translated_description = (
            await self.translate_to_english(incident.description, source_language=source_language)
            if incident.description is not None
            else None
        )

        return translated_title, translated_description

    async def _translate_with_client(self, text: str, source_language: str) -> str:
        if self._translator is None:
            return text

        try:
            translation_result = self._translator.translate_to_english(
                text,
                source_language=source_language,
            )
            if inspect.isawaitable(translation_result):
                translation_result = await translation_result

            if isinstance(translation_result, str):
                return translation_result

            translated_text = getattr(translation_result, "text", None)
            if isinstance(translated_text, str):
                return translated_text

            return text
        except Exception:
            return text
