"""Gemini provider implementation."""

from typing import Optional

from google import genai
from google.genai import types

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini-backed LLM provider."""

    def __init__(self, api_key: str, model: str, http_options: Optional[types.HttpOptions] = None) -> None:
        self._client = genai.Client(api_key=api_key, http_options=http_options)
        self._model = model

    def generate(self, prompt: str, max_tokens: int) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=max_tokens),
        )
        return response.text or ""
