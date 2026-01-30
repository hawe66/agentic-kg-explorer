"""Retrieval module — embedding and vector search."""

from .embedder import EmbeddingClient, get_embedding_client
from .vector_store import VectorStore, VectorSearchResult, get_vector_store

__all__ = [
    "EmbeddingClient",
    "get_embedding_client",
    "VectorStore",
    "VectorSearchResult",
    "get_vector_store",
]
