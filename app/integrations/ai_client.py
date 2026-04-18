from app.integrations.hazard_ai_client import AIJsonResponse, HazardAIClient


class AIClient(HazardAIClient):
    """Provider-neutral alias for JSON-completion AI calls."""


__all__ = ["AIClient", "AIJsonResponse"]
