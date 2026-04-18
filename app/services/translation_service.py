import logging
from typing import Optional, Tuple

import deepl

from app.schemas.incident_schemas import IncidentCreateRequest
from app.services.language_service import LanguageService
from app.core.config import settings

logger = logging.getLogger(__name__)

# Map ISO 639-1 codes → DeepL source language codes
# https://developers.deepl.com/docs/resources/supported-languages
DEEPL_LANGUAGE_MAP: dict[str, str] = {
    "pt": "PT",   # Portuguese (Brazil)
    "da": "DA",   # Danish
    "pl": "PL",   # Polish
    "de": "DE",   # German
    "nl": "NL",   # Dutch
    "bg": "BG",   # Bulgarian
    "ro": "RO",   # Romanian
    "zh": "ZH",   # Chinese
    "es": "ES",   # Spanish
    # "en" is intentionally excluded — English is never translated
}


class TranslationService:
    """
    Translates multilingual incident fields into English using DeepL.

    Behaviour:
      - Empty input → returns empty string.
      - English input → returns original text immediately (no API call).
      - Unknown/unsupported language → returns original text (safe default).
      - DeepL failure → logs warning, returns original text (pipeline continues).

    To swap provider: replace _call_provider() body only.
    """

    def __init__(self) -> None:
        self._language_service = LanguageService()
        self._translator: Optional[deepl.Translator] = None
        self._init_translator()

    def _init_translator(self) -> None:
        """Initialise DeepL translator from settings. Logs warning if key missing."""
        api_key = getattr(settings, "deepl_api_key", None)
        if api_key:
            self._translator = deepl.Translator(api_key)
            logger.info("DeepL translator initialised.")
        else:
            logger.warning(
                "DEEPL_API_KEY not set in environment. "
                "TranslationService will return original text unchanged."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def translate_to_english(
        self,
        text: str,
        source_language: Optional[str] = None,
    ) -> str:
        """
        Translate a single text field to English.

        Args:
            text:            Source text to translate.
            source_language: Detected ISO 639-1 language code (e.g. "da", "pl").
                             If None, service will attempt auto-detection.

        Returns:
            English translation, or original text if translation is skipped/fails.
            Empty string if input is empty.
        """
        if not text or not text.strip():
            return ""

        lang = source_language or self._language_service.detect_language(text)

        if not self._language_service.should_translate(lang):
            return text

        return self._call_provider(text, source_language=lang)

    async def translate_incident_fields(
        self,
        incident: IncidentCreateRequest,
        source_language: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Translate the title and description fields of an incident.

        Args:
            incident:        Raw incident request object.
            source_language: Detected language code. Detected from title if None.

        Returns:
            (translated_title, translated_description)
            Either value is None when the corresponding source field is None.
        """
        lang = source_language
        if lang is None and incident.title:
            lang = self._language_service.detect_language(incident.title)

        translated_title = (
            await self.translate_to_english(incident.title, source_language=lang)
            if incident.title is not None
            else None
        )

        translated_description = (
            await self.translate_to_english(incident.description, source_language=lang)
            if incident.description is not None
            else None
        )

        return translated_title, translated_description

    # ------------------------------------------------------------------
    # Provider — DeepL
    # ------------------------------------------------------------------

    def _call_provider(self, text: str, source_language: Optional[str]) -> str:
        """
        Translate text to English using DeepL Free/Pro API.

        Uses a short sample (first 500 chars) since records are brief
        and to stay well within free-tier character limits.

        Args:
            text:            Text to translate.
            source_language: ISO 639-1 source language code.

        Returns:
            DeepL English translation, or original text on any failure.
        """
        if self._translator is None:
            logger.warning("DeepL not initialised. Returning original text.")
            return text

        # Short sample guard — keeps usage within free tier for small reports
        sample = text[:500]

        deepl_source = DEEPL_LANGUAGE_MAP.get(source_language or "", None)

        try:
            result = self._translator.translate_text(
                sample,
                source_lang=deepl_source,   # None = DeepL auto-detect
                target_lang="EN-US",
            )
            translated = result.text
            logger.debug(
                "DeepL translated %d chars (%s → EN-US).",
                len(sample),
                deepl_source or "auto",
            )
            return translated
        except deepl.DeepLException as exc:
            logger.warning("DeepL translation failed: %s. Returning original text.", exc)
            return text
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected translation error: %s. Returning original text.", exc)
            return text