import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ISO 639-1 codes for languages used at Danfoss sites
SUPPORTED_LANGUAGE_CODES = {
    "pt",  # Portuguese
    "da",  # Danish
    "en",  # English
    "pl",  # Polish
    "de",  # German
    "nl",  # Dutch
    "bg",  # Bulgarian
    "ro",  # Romanian
    "zh",  # Chinese
    "es",  # Spanish
}


class LanguageService:
    """
    Detects the source language of incident text and decides whether
    translation to English is required.

    MVP strategy:
      1. Try langdetect (lightweight, offline, no API key required).
      2. Fall back to None if detection fails or text is too short.

    Replace detect_language() body to plug in Azure Cognitive Services,
    Google Cloud Translation detect, or any other provider.
    """

    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect source language from text.

        Args:
            text: Cleaned analysis text from TextCleaningService.

        Returns:
            ISO 639-1 language code (e.g. "en", "da", "pl", "zh").
            None if language cannot be detected (text too short, ambiguous,
            or detection library not available).
        """
        if not text or len(text.strip()) < 10:
            logger.debug("Text too short for language detection, returning None.")
            return None

        try:
            from langdetect import detect, LangDetectException  # type: ignore

            code = detect(text)
            logger.debug("langdetect result: %s", code)
            return code
        except ImportError:
            logger.warning(
                "langdetect not installed. "
                "Run `pip install langdetect` or swap in another provider. "
                "Falling back to None."
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Language detection failed: %s", exc)
            return None

    def should_translate(self, language_code: Optional[str]) -> bool:
        """
        Decide whether translation to English is needed.

        Args:
            language_code: ISO 639-1 code returned by detect_language(),
                           or None when detection was not possible.

        Returns:
            True  – language is known, non-English → translation required.
            False – language is English, unknown/None, or unsupported
                    (safe default: do not translate when uncertain).
        """
        if language_code is None:
            return False
        if language_code == "en":
            return False
        # Translate any recognised non-English Danfoss-site language.
        # Unknown/exotic codes → False (safe default, avoid corrupting text).
        return language_code in SUPPORTED_LANGUAGE_CODES