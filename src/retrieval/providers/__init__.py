"""Embedding provider abstraction layer."""

from .base import EmbeddingProvider
from .router import get_embedding_provider

__all__ = ["EmbeddingProvider", "get_embedding_provider"]
