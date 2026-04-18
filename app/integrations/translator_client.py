from app.core.config import get_settings


DEEPL_PROVIDER = "deepl"
DEEPL_TARGET_LANGUAGE = "EN-US"


class DeepLTranslatorClient:
    def __init__(self, api_key: str) -> None:
        import deepl

        self._translator = deepl.Translator(api_key)

    async def translate_to_english(
        self,
        text: str,
        source_language: str | None = None,
    ) -> str:
        source_lang = source_language.upper() if source_language else None
        result = self._translator.translate_text(
            text,
            source_lang=source_lang,
            target_lang=DEEPL_TARGET_LANGUAGE,
        )
        return result.text


def build_translator_client() -> DeepLTranslatorClient | None:
    settings = get_settings()
    if settings.translator_provider.lower() == DEEPL_PROVIDER and settings.deepl_api_key:
        return DeepLTranslatorClient(settings.deepl_api_key)
    return None
