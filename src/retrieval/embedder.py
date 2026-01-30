"""OpenAI embedding client for vector search."""

import os
from typing import Optional

from openai import OpenAI


class EmbeddingClient:
    """Wrapper around OpenAI embeddings API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        http_client=None,
    ):
        kwargs = {"api_key": api_key}
        if http_client is not None:
            kwargs["http_client"] = http_client
        self._client = OpenAI(**kwargs)
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        response = self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]

    def embed_single(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: String to embed.

        Returns:
            Embedding vector.
        """
        return self.embed_texts([text])[0]


def get_embedding_client() -> Optional[EmbeddingClient]:
    """Create an EmbeddingClient from environment variables.

    Returns:
        EmbeddingClient if OPENAI_API_KEY is set, else None.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None

    # Build SSL-aware httpx client if SSL_CERT_FILE is set
    http_client = None
    cafile = os.getenv("SSL_CERT_FILE")
    if cafile and os.path.isfile(cafile):
        from openai import DefaultHttpxClient
        http_client = DefaultHttpxClient(verify=cafile)

    return EmbeddingClient(api_key=api_key, http_client=http_client)
