"""Graph retrieval node for executing Cypher queries against Neo4j."""

from typing import Optional

from config.settings import get_settings
from src.graph.client import Neo4jClient

from ..state import AgentState


def retrieve_from_graph(state: AgentState) -> AgentState:
    """Execute Cypher query and/or vector search and retrieve results.

    Supports three retrieval modes:
    - graph_only: Cypher query against Neo4j (original behavior)
    - vector_first: embed query → ChromaDB similarity → enrich from Neo4j
    - hybrid: Cypher + ChromaDB → merge results

    Args:
        state: Current agent state with search_strategy

    Returns:
        Updated state with kg_results, vector_results, and cypher_executed
    """
    strategy = state.get("search_strategy")

    if not strategy:
        state["error"] = "No search strategy available"
        return state

    retrieval_type = strategy.get("retrieval_type", "graph_only")

    if retrieval_type == "none":
        state["kg_results"] = []
        state["cypher_executed"] = []
        return state

    # --- Vector search ---
    if retrieval_type in ("vector_first", "hybrid"):
        vector_results = _run_vector_search(strategy.get("vector_query", ""))
        state["vector_results"] = vector_results
        if vector_results:
            print(f"[Graph Retriever] Vector search returned {len(vector_results)} results")

    # --- Graph search ---
    cypher_template = strategy.get("cypher_template")
    parameters = strategy.get("parameters", {})

    if retrieval_type == "vector_first" and not cypher_template:
        # No Cypher template; enrich vector results from Neo4j instead
        vector_results = state.get("vector_results") or []
        if vector_results:
            enriched = _enrich_from_neo4j(vector_results)
            state["kg_results"] = enriched
            state["cypher_executed"] = ["(vector enrichment)"]
        else:
            state["kg_results"] = []
            state["cypher_executed"] = []
        return state

    if not cypher_template:
        error_msg = strategy.get("error", "No Cypher template available")
        state["error"] = error_msg
        state["kg_results"] = []
        state["cypher_executed"] = []
        return state

    print(f"[Graph Retriever] Executing Cypher with params: {parameters}")

    try:
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()

        results = client.run_cypher(cypher_template, parameters)
        kg_results = _serialize_results(results)

        state["kg_results"] = kg_results
        state["cypher_executed"] = [cypher_template]

        print(f"[Graph Retriever] Retrieved {len(kg_results)} graph results")

        client.close()

    except Exception as e:
        print(f"[Graph Retriever] Graph error: {e}")
        state["error"] = f"Graph retrieval failed: {str(e)}"
        state["kg_results"] = []
        state["cypher_executed"] = []

    return state


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def _run_vector_search(query_text: str, n_results: int = 5) -> list[dict]:
    """Embed query and search ChromaDB. Returns list of dicts (serializable)."""
    if not query_text:
        return []
    try:
        from src.retrieval.embedder import get_embedding_client
        from src.retrieval.vector_store import get_vector_store

        embedder = get_embedding_client()
        store = get_vector_store()
        if embedder is None or not store.is_available:
            return []

        embedding = embedder.embed_single(query_text)
        results = store.query(query_embedding=embedding, n_results=n_results)

        return [
            {
                "node_id": r.node_id,
                "node_label": r.node_label,
                "text": r.text,
                "field": r.field,
                "score": r.score,
            }
            for r in results
        ]
    except Exception as e:
        print(f"[Graph Retriever] Vector search error: {e}")
        return []


def _enrich_from_neo4j(vector_results: list[dict]) -> list[dict]:
    """Fetch full node data from Neo4j for vector-matched node IDs."""
    node_ids = list({r["node_id"] for r in vector_results})
    if not node_ids:
        return []

    try:
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()

        enrichment_query = """
        MATCH (n) WHERE n.id IN $node_ids
        OPTIONAL MATCH (n)-[r]-(related)
        RETURN n,
               collect(DISTINCT {node: related, rel_type: type(r)}) as connections
        """
        results = client.run_cypher(enrichment_query, {"node_ids": node_ids})
        client.close()

        return _serialize_results(results)
    except Exception as e:
        print(f"[Graph Retriever] Enrichment error: {e}")
        return []


def _serialize_results(results: list) -> list[dict]:
    """Convert Neo4j results to JSON-serializable format.

    Args:
        results: Raw results from Neo4j query

    Returns:
        List of serialized result dictionaries
    """
    serialized = []

    for record in results:
        record_dict = {}

        for key, value in record.items():
            # Handle Neo4j Node objects
            if hasattr(value, "labels") and hasattr(value, "items"):
                # It's a Node
                record_dict[key] = {
                    "labels": list(value.labels),
                    "properties": dict(value.items()),
                    "id": value.element_id if hasattr(value, "element_id") else None,
                }
            # Handle Neo4j Relationship objects
            elif hasattr(value, "type") and hasattr(value, "items"):
                # It's a Relationship
                record_dict[key] = {
                    "type": value.type,
                    "properties": dict(value.items()),
                    "id": value.element_id if hasattr(value, "element_id") else None,
                }
            # Handle lists (might contain nodes/relationships)
            elif isinstance(value, list):
                record_dict[key] = [_serialize_single_value(v) for v in value]
            # Handle primitives
            else:
                record_dict[key] = _serialize_single_value(value)

        serialized.append(record_dict)

    return serialized


def _serialize_single_value(value):
    """Serialize a single value (handles nodes, relationships, primitives)."""
    if hasattr(value, "labels") and hasattr(value, "items"):
        # Node
        return {
            "labels": list(value.labels),
            "properties": dict(value.items()),
        }
    elif hasattr(value, "type") and hasattr(value, "items"):
        # Relationship
        return {
            "type": value.type,
            "properties": dict(value.items()),
        }
    elif isinstance(value, dict):
        # Already a dict, recurse
        return {k: _serialize_single_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_serialize_single_value(v) for v in value]
    else:
        # Primitive value
        return value
