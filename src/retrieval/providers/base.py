"""Embedding provider interface."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Minimal interface for text embedding.

    All embedding providers must implement this interface.
    Providers can be swapped via EMBEDDING_PROVIDER env var.
    """

    model: str  # The embedding model name

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        raise NotImplementedError

    def embed_single(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: String to embed.

        Returns:
            Embedding vector.
        """
        return self.embed_texts([text])[0]
