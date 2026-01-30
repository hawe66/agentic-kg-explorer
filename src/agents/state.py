"""Agent state definition for LangGraph pipeline."""

from typing import TypedDict, Literal, Optional


class AgentState(TypedDict):
    """State schema for the knowledge graph exploration agent.

    This state flows through the LangGraph pipeline and gets updated
    by each node (Intent Classifier → Search Planner → Graph Retriever → Synthesizer).
    """

    # ===== Input =====
    user_query: str
    """Original user question"""

    # ===== Intent Classification =====
    intent: Optional[Literal["lookup", "path", "comparison", "expansion"]]
    """
    Query intent type:
    - lookup: Single concept lookup (e.g., "What is ReAct?")
    - path: Relationship exploration (e.g., "Methods for Planning principle?")
    - comparison: Multi-concept comparison (e.g., "CrewAI vs AutoGen")
    - expansion: Information not in graph (requires web search in Phase 3)
    """

    entities: Optional[list[str]]
    """Extracted entities from the query (e.g., ["ReAct", "LangChain"])"""

    # ===== Search Planning =====
    search_strategy: Optional[dict]
    """
    Search strategy including:
    - cypher_template: Cypher query template
    - parameters: Query parameters
    - retrieval_type: "graph_only" | "vector_first" | "hybrid"
    """

    # ===== Graph Retrieval =====
    kg_results: Optional[list[dict]]
    """Results from Neo4j queries"""

    cypher_executed: Optional[list[str]]
    """Executed Cypher queries for debugging/transparency"""

    # ===== Synthesis =====
    answer: Optional[str]
    """Final answer to the user"""

    sources: Optional[list[dict]]
    """
    Sources used in the answer:
    [{"type": "Method", "id": "m:react", "name": "ReAct"}, ...]
    """

    confidence: Optional[float]
    """Confidence score (0.0-1.0) for the answer"""

    # ===== Error Handling =====
    error: Optional[str]
    """Error message if any step fails"""
