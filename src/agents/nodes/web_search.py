"""Web search node using Tavily API with ChromaDB persistence."""

import hashlib
import os
from datetime import datetime, timezone

from ..state import AgentState


def web_search(state: AgentState) -> AgentState:
    """Execute web search when KG has no results or intent is expansion.

    Results are persisted to ChromaDB for future similarity searches.

    Args:
        state: Current agent state with kg_results and vector_results

    Returns:
        Updated state with web_results
    """
    intent = state.get("intent")
    kg_results = state.get("kg_results") or []
    vector_results = state.get("vector_results") or []

    # Skip if we already have results (unless expansion)
    has_results = bool(kg_results) or bool(vector_results)
    if has_results and intent != "expansion":
        state["web_results"] = []
        state["web_query"] = None
        return state

    query = state.get("user_query", "")
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        print("[Web Search] TAVILY_API_KEY not set, skipping")
        state["web_results"] = []
        state["web_query"] = None
        return state

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=False,
        )

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
            }
            for r in response.get("results", [])
        ]

        # Persist to ChromaDB
        _persist_web_results(results, query)

        state["web_results"] = results
        state["web_query"] = query
        print(f"[Web Search] Found {len(results)} results, persisted to ChromaDB")

    except Exception as e:
        print(f"[Web Search] Error: {e}")
        state["web_results"] = []
        state["web_query"] = query

    return state


def _persist_web_results(results: list[dict], query: str) -> None:
    """Persist web search results to ChromaDB.

    ID format: web:{url_hash}:{chunk_index}
    """
    if not results:
        return

    try:
        from src.retrieval.embedder import get_embedding_client
        from src.retrieval.vector_store import get_vector_store

        embedder = get_embedding_client()
        store = get_vector_store()

        if embedder is None:
            print("[Web Search] No embedding client, skipping persistence")
            return

        collected_at = datetime.now(timezone.utc).isoformat()

        ids = []
        texts = []
        metadatas = []

        for i, r in enumerate(results):
            url = r.get("url", "")
            content = r.get("content", "")
            title = r.get("title", "")

            if not url or not content:
                continue

            # Generate URL hash for ID
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            entry_id = f"web:{url_hash}:{i}"

            # Build text for embedding (title + content)
            text = f"[Web] {title}\n{content}" if title else content

            # Metadata (no None values for ChromaDB)
            metadata = {
                "source_type": "web_search",
                "source_id": url_hash,
                "source_url": url,
                "collected_at": collected_at,
                "collector": "web_search_expander",
                "node_id": "",  # Not linked to KG node yet
                "node_label": "",
                "title": title or url,
                "chunk_index": i,
                "total_chunks": len(results),
                "search_query": query,  # Track what query found this
            }

            ids.append(entry_id)
            texts.append(text)
            metadatas.append(metadata)

        if not texts:
            return

        # Embed and store
        embeddings = embedder.embed_texts(texts)
        store.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        print(f"[Web Search] Persisted {len(ids)} web results to ChromaDB")

    except Exception as e:
        print(f"[Web Search] Persistence error: {e}")
