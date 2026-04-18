from typing import Any, Dict
import json

from pydantic import BaseModel
from openai import AsyncOpenAI

from app.core.config import get_settings


class AIJsonResponse(BaseModel):
    data: Dict[str, Any]
    raw_text: str


class HazardAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.hazard_ai_model

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> AIJsonResponse:
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