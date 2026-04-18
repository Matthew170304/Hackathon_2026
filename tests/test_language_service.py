import pytest

from app.services.language import LanguageService


class TestLanguageService:
    def setup_method(self):
        self.service = LanguageService()

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("", None),
            ("   ", None),
            ("The worker and the supervisor inspected the area after the incident.", "en"),
            ("Håndtaget er løst, og området skal afspærres.", "da"),
            ("Operator zgłosił awarię i łączność została przerwana.", "pl"),
            ("设备需要检查并且需要立即停机处理。", "zh"),
        ],
    )
    def test_detect_language_returns_expected_code(self, text, expected):
        assert self.service.detect_language(text) == expected

    @pytest.mark.parametrize(
        "language_code, expected",
        [
            (None, False),
            ("en", False),
            ("da", True),
            ("pl", True),
            ("sl", True),
            ("zh", True),
            ("xx", False),
        ],
    )
    def test_should_translate_uses_expected_rules(self, language_code, expected):
        assert self.service.should_translate(language_code) is expected
