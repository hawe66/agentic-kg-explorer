"""ChromaDB vector store for semantic search over KG nodes and web results."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import chromadb


@dataclass
class VectorSearchResult:
    """A single result from vector similarity search.

    Unified schema for both KG nodes and web search results.
    """

    # Identity
    source_type: str       # "kg_node" | "web_search" | "paper" | "user_note"
    source_id: str         # node_id for KG, URL for web
    source_url: Optional[str]  # URL for web results

    # KG linkage (may be None for web results not linked to KG)
    node_id: Optional[str]     # e.g. "m:react"
    node_label: Optional[str]  # e.g. "Method"

    # Content
    title: str             # display title
    text: str              # matched text (unified node text or web content)
    score: float           # cosine similarity (0-1, higher is more similar)

    # Provenance
    collected_at: Optional[str]  # ISO timestamp
    collector: Optional[str]     # "generate_embeddings.py" | "web_search_expander"


class VectorStore:
    """ChromaDB wrapper with persistent storage."""

    def __init__(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = "kg_nodes_v2",  # New collection for new schema
    ):
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        """Delete and recreate the collection."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
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

    def delete_by_prefix(self, prefix: str) -> None:
        """Delete all entries with IDs starting with prefix.

        Useful for removing all web results (prefix='web:') or all KG nodes (prefix='kg:').
        """
        # ChromaDB doesn't support prefix deletion directly, so we need to get all IDs first
        all_data = self._collection.get()
        if not all_data or not all_data["ids"]:
            return

        ids_to_delete = [id_ for id_ in all_data["ids"] if id_.startswith(prefix)]
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        source_type: Optional[str] = None,
    ) -> list[VectorSearchResult]:
        """Similarity search by embedding vector.

        Args:
            query_embedding: Query embedding vector.
            n_results: Number of results to return.
            source_type: Filter by source type ("kg_node", "web_search", etc.)

        Returns:
            List of VectorSearchResult sorted by similarity.
        """
        where_filter = None
        if source_type:
            where_filter = {"source_type": source_type}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
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
                # Identity
                source_type=meta.get("source_type", "kg_node"),
                source_id=meta.get("source_id", doc_id),
                source_url=meta.get("source_url"),
                # KG linkage
                node_id=meta.get("node_id"),
                node_label=meta.get("node_label"),
                # Content
                title=meta.get("title", ""),
                text=doc or "",
                score=round(similarity, 4),
                # Provenance
                collected_at=meta.get("collected_at"),
                collector=meta.get("collector"),
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
