"""Provider interface for runtime LLM usage."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Minimal interface for text generation."""
    max_classify_tokens: int
    max_synthesize_tokens: int

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate a completion from a prompt."""
        raise NotImplementedError
