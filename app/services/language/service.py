from __future__ import annotations

import re
from typing import Optional


SUPPORTED_LANGUAGE_CODES = {
    "en",
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

MIN_TEXT_LENGTH_FOR_DETECTION = 12

_CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04ff]")
_DANISH_PATTERN = re.compile(r"[æøå]|\b(ikke|hånd|arbejde|maskine|adgang)\b", re.IGNORECASE)
_POLISH_PATTERN = re.compile(r"[ąćęłńóśźż]|\b(zgłosił|maszyna|wypadek|awaria|pracownik)\b", re.IGNORECASE)
_SLOVENIAN_PATTERN = re.compile(r"[čšž]|\b(nesreča|delavec|napaka|stroj)\b", re.IGNORECASE)
_ROMANIAN_PATTERN = re.compile(r"[ăâîșț]|\b(angajat|utilaj|accident|defecțiune)\b", re.IGNORECASE)
_SPANISH_PATTERN = re.compile(r"[ñáéíóú]|\b(trabajador|incidente|máquina|riesgo)\b", re.IGNORECASE)
_PORTUGUESE_PATTERN = re.compile(r"[ãõç]|\b(trabalhador|incidente|máquina|risco)\b", re.IGNORECASE)
_GERMAN_PATTERN = re.compile(r"[äöüß]|\b(unfall|arbeiter|gefahr)\b", re.IGNORECASE)
_DUTCH_PATTERN = re.compile(r"\b(het|een|niet|werknemer|ongeval)\b", re.IGNORECASE)
_ENGLISH_PATTERN = re.compile(r"\b(the|and|with|incident|worker|machine|safety)\b", re.IGNORECASE)


class LanguageService:
    def detect_language(self, text: str) -> Optional[str]:
        if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_DETECTION:
            return None

        normalized_text = text.strip()

        if _CHINESE_PATTERN.search(normalized_text):
            return "zh"
        if _CYRILLIC_PATTERN.search(normalized_text):
            return "bg"
        if _DANISH_PATTERN.search(normalized_text):
            return "da"
        if _POLISH_PATTERN.search(normalized_text):
            return "pl"
        if _SLOVENIAN_PATTERN.search(normalized_text):
            return "sl"
        if _ROMANIAN_PATTERN.search(normalized_text):
            return "ro"
        if _SPANISH_PATTERN.search(normalized_text):
            return "es"
        if _PORTUGUESE_PATTERN.search(normalized_text):
            return "pt"
        if _GERMAN_PATTERN.search(normalized_text):
            return "de"
        if _DUTCH_PATTERN.search(normalized_text):
            return "nl"
        if _ENGLISH_PATTERN.search(normalized_text):
            return "en"

        return None

    def should_translate(self, language_code: Optional[str]) -> bool:
        return (
            language_code is not None
            and language_code != "en"
            and language_code in SUPPORTED_LANGUAGE_CODES
        )
