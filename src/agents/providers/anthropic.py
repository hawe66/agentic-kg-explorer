"""Anthropic provider implementation."""

from typing import Optional

from anthropic import Anthropic

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic-backed LLM provider."""

    def __init__(self, api_key: str, model: str, http_client: Optional[object] = None) -> None:
        self._client = Anthropic(api_key=api_key, http_client=http_client)
        self._model = model

    def generate(self, prompt: str, max_tokens: int) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
