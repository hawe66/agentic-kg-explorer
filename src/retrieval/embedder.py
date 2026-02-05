"""Embedding client — backward-compatible wrapper around provider abstraction.

New code should use:
    from src.retrieval.providers import get_embedding_provider

Legacy code can continue using:
    from src.retrieval.embedder import get_embedding_client
"""

from typing import Optional

from .providers import EmbeddingProvider, get_embedding_provider


# Alias for backward compatibility
EmbeddingClient = EmbeddingProvider


def get_embedding_client() -> Optional[EmbeddingProvider]:
    """Get an embedding provider instance.

    This is a backward-compatible alias for get_embedding_provider().
    New code should use get_embedding_provider() directly.

    Returns:
        EmbeddingProvider instance or None if unavailable.
    """
    return get_embedding_provider()
