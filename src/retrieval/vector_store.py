"""ChromaDB vector store for semantic search over KG nodes."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import chromadb


@dataclass
class VectorSearchResult:
    """A single result from vector similarity search."""

    node_id: str       # e.g. "m:react"
    node_label: str    # e.g. "Method"
    text: str          # matched text
    field: str         # "description" | "name" | "abstract"
    score: float       # cosine similarity (0-1, higher is more similar)


class VectorStore:
    """ChromaDB wrapper with persistent storage."""

    def __init__(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = "kg_nodes",
    ):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Add or update entries in the collection."""
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[VectorSearchResult]:
        """Similarity search by embedding vector.

        Args:
            query_embedding: Query embedding vector.
            n_results: Number of results to return.

        Returns:
            List of VectorSearchResult sorted by similarity.
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        parsed: list[VectorSearchResult] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return parsed

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else [None] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for doc_id, doc, meta, distance in zip(ids, documents, metadatas, distances):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 - (distance / 2)
            similarity = 1.0 - (distance / 2.0)
            parsed.append(VectorSearchResult(
                node_id=meta.get("node_id", doc_id),
                node_label=meta.get("node_label", "Unknown"),
                text=doc or "",
                field=meta.get("field", "unknown"),
                score=round(similarity, 4),
            ))

        return parsed

    @property
    def count(self) -> int:
        """Number of entries in the collection."""
        return self._collection.count()

    @property
    def is_available(self) -> bool:
        """Whether the store has any data."""
        return self.count > 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the singleton VectorStore instance."""
    global _instance
    if _instance is None:
        persist_dir = str(Path(__file__).resolve().parents[2] / "data" / "chroma")
        _instance = VectorStore(persist_dir=persist_dir)
    return _instance
