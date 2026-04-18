import pytest

from app.schemas.incident_schemas import IncidentCreateRequest
from app.services.translation import TranslationService


class FakeTranslator:
    def __init__(self):
        self.calls = []

    async def translate_to_english(self, text: str, source_language: str | None = None) -> str:
        self.calls.append((text, source_language))
        return f"translated:{source_language}:{text}"


class TestTranslationService:
    def setup_method(self):
        self.service = TranslationService()

    @pytest.mark.asyncio
    async def test_translate_to_english_returns_empty_string_for_empty_input(self):
        assert await self.service.translate_to_english("") == ""

    @pytest.mark.asyncio
    async def test_translate_to_english_returns_original_text_without_source_language(self):
        assert await self.service.translate_to_english("Some text") == "Some text"

    @pytest.mark.asyncio
    async def test_translate_to_english_returns_original_text_for_english(self):
        assert await self.service.translate_to_english("This is English text", source_language="en") == "This is English text"

    @pytest.mark.asyncio
    async def test_translate_to_english_returns_original_text_for_unsupported_language(self):
        assert await self.service.translate_to_english("Some text", source_language="xx") == "Some text"

    @pytest.mark.asyncio
    async def test_translate_to_english_uses_injected_translator(self):
        translator = FakeTranslator()
        service = TranslationService(translator_client=translator)

        result = await service.translate_to_english("Dansk tekst", source_language="da")

        assert result == "translated:da:Dansk tekst"
        assert translator.calls == [("Dansk tekst", "da")]

    @pytest.mark.asyncio
    async def test_translate_incident_fields_returns_translated_title_and_description(self):
        incident = IncidentCreateRequest(
            title="Titel",
            description="Beskrivelse",
        )

        translator = FakeTranslator()
        service = TranslationService(translator_client=translator)
        translated_title, translated_description = await service.translate_incident_fields(incident, source_language="da")

        assert translated_title == "translated:da:Titel"
        assert translated_description == "translated:da:Beskrivelse"
        assert translator.calls == [("Titel", "da"), ("Beskrivelse", "da")]

    @pytest.mark.asyncio
    async def test_translate_incident_fields_preserves_missing_fields(self):
        incident = IncidentCreateRequest(
            title=None,
            description="Beskrivelse",
        )

        translator = FakeTranslator()
        service = TranslationService(translator_client=translator)
        translated_title, translated_description = await service.translate_incident_fields(incident, source_language="da")

        assert translated_title is None
        assert translated_description == "translated:da:Beskrivelse"
