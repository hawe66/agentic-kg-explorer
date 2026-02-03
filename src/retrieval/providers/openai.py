"""OpenAI embedding provider."""

from openai import OpenAI

from .base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding API wrapper."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        http_client=None,
    ):
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key.
            model: Embedding model name (default: text-embedding-3-small).
            http_client: Optional httpx client for SSL configuration.
        """
        kwargs = {"api_key": api_key}
        if http_client is not None:
            kwargs["http_client"] = http_client
        self._client = OpenAI(**kwargs)
        self.model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts via OpenAI API.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        response = self._client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]
