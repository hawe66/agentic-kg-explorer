"""Graph retrieval node for executing Cypher queries against Neo4j."""

from config.settings import get_settings
from src.graph.client import Neo4jClient

from ..state import AgentState


def retrieve_from_graph(state: AgentState) -> AgentState:
    """Execute Cypher query and retrieve results from Neo4j.

    Args:
        state: Current agent state with search_strategy

    Returns:
        Updated state with kg_results and cypher_executed
    """
    strategy = state.get("search_strategy")

    if not strategy:
        state["error"] = "No search strategy available"
        return state

    # Check if query can be executed
    retrieval_type = strategy.get("retrieval_type")
    if retrieval_type == "none":
        # Expansion or error case
        state["kg_results"] = []
        state["cypher_executed"] = []
        return state

    cypher_template = strategy.get("cypher_template")
    parameters = strategy.get("parameters", {})

    if not cypher_template:
        error_msg = strategy.get("error", "No Cypher template available")
        state["error"] = error_msg
        state["kg_results"] = []
        state["cypher_executed"] = []
        return state

    print(f"[Graph Retriever] Executing query with params: {parameters}")

    try:
        # Connect to Neo4j
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()

        # Execute query
        results = client.run_cypher(cypher_template, parameters)

        # Convert results to serializable format
        kg_results = _serialize_results(results)

        state["kg_results"] = kg_results
        state["cypher_executed"] = [cypher_template]

        print(f"[Graph Retriever] Retrieved {len(kg_results)} results")

        # Close connection
        client.close()

    except Exception as e:
        print(f"[Graph Retriever] Error: {e}")
        state["error"] = f"Graph retrieval failed: {str(e)}"
        state["kg_results"] = []
        state["cypher_executed"] = []

    return state


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
