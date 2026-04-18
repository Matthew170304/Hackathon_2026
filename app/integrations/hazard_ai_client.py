from typing import Any, Dict
import json

from pydantic import BaseModel

from app.core.config import get_settings

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - exercised when optional SDK is absent.
    AsyncOpenAI = None


class AIJsonResponse(BaseModel):
    data: Dict[str, Any]
    raw_text: str


class HazardAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if (
                AsyncOpenAI is not None
                and settings.ai_provider.lower() == "openai"
                and settings.openai_api_key
            )
            else None
        )
        self.model = settings.hazard_ai_model

    # noinspection PyTypeChecker
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> AIJsonResponse:
        if self.client is None:
            return self._complete_json_by_rules(user_prompt)

        response = await self.client.responses.create(
            model=self.model,
            temperature=temperature,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "strict": True,
                    "name": "hazard_classification",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "confidence": {"type": "number"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["label", "confidence", "explanation"],
                        "additionalProperties": False,
                    },
                }
            },
        )

        raw_text = ""

        if hasattr(response, "output_text") and response.output_text:
            raw_text = response.output_text
        else:
            try:
                raw_text = response.output[0].content[0].text
            except Exception:
                raw_text = ""
                print(f"Failed to extract AI response text, response:\n{response}")

        try:
            data = json.loads(raw_text)
        except Exception:
            data = {}

        return AIJsonResponse(
            data=data,
            raw_text=raw_text,
        )

    @staticmethod
    def _complete_json_by_rules(user_prompt: str) -> AIJsonResponse:
        prompt = user_prompt.lower()

        if "source cause" in prompt:
            data = _classify_cause_prompt(prompt)
        else:
            data = _classify_hazard_prompt(prompt)

        return AIJsonResponse(data=data, raw_text=json.dumps(data))


def _classify_cause_prompt(prompt: str) -> Dict[str, Any]:
    if any(keyword in prompt for keyword in ("procedure", "instruction", "step was skipped")):
        label = "Procedures"
    elif any(keyword in prompt for keyword in ("distracted", "rushed", "not paying attention", "human error")):
        label = "Human Factors"
    elif any(keyword in prompt for keyword in ("training", "not trained", "did not know")):
        label = "Competences"
    elif _contains_any(prompt, ("ppe", "gloves", "helmet")):
        label = "Personal Protective Equipment"
    elif any(keyword in prompt for keyword in ("clutter", "debris", "housekeeping")):
        label = "Housekeeping"
    else:
        label = "Unknown"

    if label == "Unknown":
        confidence = 0.2
    else:
        confidence = 0.8

    return {
        "label": label,
        "confidence": confidence,
        "explanation": "Local rule fallback used because no AI client is configured.",
    }


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        if len(keyword) <= 3:
            if __import__("re").search(rf"\b{keyword}\b", text):
                return True
        elif keyword in text:
            return True
    return False


def _classify_hazard_prompt(prompt: str) -> Dict[str, Any]:
    if any(keyword in prompt for keyword in ("slip", "trip", "fall", "wet floor")):
        label = "Physical Hazards"
    elif any(keyword in prompt for keyword in ("forklift", "vehicle", "traffic", "pedestrian")):
        label = "Vehicle & Traffic Hazards"
    elif any(keyword in prompt for keyword in ("electric", "shock", "wire", "voltage")):
        label = "Electrical Hazards"
    elif any(keyword in prompt for keyword in ("chemical", "spill", "leak", "fumes")):
        label = "Chemical Hazards"
    elif any(keyword in prompt for keyword in ("machine", "guard", "moving part", "pinch")):
        label = "Mechanical / Equipment Hazards"
    else:
        label = "Unknown"

    if label == "Unknown":
        confidence = 0.2
    else:
        confidence = 0.8

    return {
        "label": label,
        "confidence": confidence,
        "explanation": "Local rule fallback used because no AI client is configured.",
    }
