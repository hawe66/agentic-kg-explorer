"""Search planning node for generating Cypher query strategies."""

from ..state import AgentState


# Cypher query templates for different intents
CYPHER_TEMPLATES = {
    "lookup_method": """
        // Find method by name (case-insensitive)
        MATCH (m:Method)
        WHERE toLower(m.name) CONTAINS toLower($entity)
           OR m.id = $entity
        OPTIONAL MATCH (m)-[addr:ADDRESSES]->(p:Principle)
        OPTIONAL MATCH (i:Implementation)-[impl:IMPLEMENTS]->(m)
        RETURN m,
               collect(DISTINCT {principle: p, role: addr.role, weight: addr.weight}) as principles,
               collect(DISTINCT {implementation: i, support_level: impl.support_level}) as implementations
        LIMIT 10
    """,
    "lookup_implementation": """
        // Find implementation by name
        MATCH (i:Implementation)
        WHERE toLower(i.name) CONTAINS toLower($entity)
           OR i.id = $entity
        OPTIONAL MATCH (i)-[impl:IMPLEMENTS]->(m:Method)
        OPTIONAL MATCH (m)-[addr:ADDRESSES]->(p:Principle)
        RETURN i,
               collect(DISTINCT {method: m, support_level: impl.support_level}) as methods,
               collect(DISTINCT p) as principles
        LIMIT 10
    """,
    "lookup_principle": """
        // Find principle by name
        MATCH (p:Principle)
        WHERE toLower(p.name) CONTAINS toLower($entity)
           OR p.id = $entity
        OPTIONAL MATCH (m:Method)-[addr:ADDRESSES]->(p)
        OPTIONAL MATCH (i:Implementation)-[:IMPLEMENTS]->(m)
        RETURN p,
               collect(DISTINCT {method: m, role: addr.role, weight: addr.weight}) as methods,
               count(DISTINCT i) as implementation_count
        LIMIT 10
    """,
    "path_principle_to_methods": """
        // Find methods that address a principle
        MATCH (p:Principle)
        WHERE toLower(p.name) CONTAINS toLower($entity)
           OR p.id = $entity
        MATCH (m:Method)-[addr:ADDRESSES]->(p)
        OPTIONAL MATCH (i:Implementation)-[impl:IMPLEMENTS]->(m)
        RETURN p, m, addr,
               collect(DISTINCT {implementation: i, support_level: impl.support_level}) as implementations
        ORDER BY addr.weight DESC
        LIMIT 20
    """,
    "path_method_to_implementations": """
        // Find implementations of a method
        MATCH (m:Method)
        WHERE toLower(m.name) CONTAINS toLower($entity)
           OR m.id = $entity
        MATCH (i:Implementation)-[impl:IMPLEMENTS]->(m)
        OPTIONAL MATCH (m)-[addr:ADDRESSES]->(p:Principle)
        RETURN m, i, impl,
               collect(DISTINCT {principle: p, role: addr.role}) as principles
        ORDER BY impl.support_level
        LIMIT 20
    """,
    "path_implementation_to_principles": """
        // Find principles supported by an implementation
        MATCH (i:Implementation)
        WHERE toLower(i.name) CONTAINS toLower($entity)
           OR i.id = $entity
        MATCH (i)-[impl:IMPLEMENTS]->(m:Method)-[addr:ADDRESSES]->(p:Principle)
        RETURN i, m, p, impl, addr
        ORDER BY p.name, addr.weight DESC
        LIMIT 30
    """,
    "comparison": """
        // Compare two implementations
        MATCH (i1:Implementation), (i2:Implementation)
        WHERE (toLower(i1.name) CONTAINS toLower($entity1) OR i1.id = $entity1)
          AND (toLower(i2.name) CONTAINS toLower($entity2) OR i2.id = $entity2)
        OPTIONAL MATCH (i1)-[impl1:IMPLEMENTS]->(m1:Method)
        OPTIONAL MATCH (i2)-[impl2:IMPLEMENTS]->(m2:Method)
        OPTIONAL MATCH (m1)-[:ADDRESSES]->(p:Principle)<-[:ADDRESSES]-(m2)
        RETURN i1, i2,
               collect(DISTINCT m1) as methods1,
               collect(DISTINCT m2) as methods2,
               collect(DISTINCT p) as common_principles
    """,
}


def plan_search(state: AgentState) -> AgentState:
    """Plan search strategy based on intent and entities.

    Args:
        state: Current agent state with intent and entities

    Returns:
        Updated state with search_strategy
    """
    intent = state.get("intent")
    entities = state.get("entities", [])

    if not intent:
        state["error"] = "No intent classified"
        return state

    print(f"[Search Planner] Planning for intent: {intent}, entities: {entities}")

    # Select appropriate Cypher template and parameters
    if intent == "lookup":
        strategy = _plan_lookup(entities)
    elif intent == "path":
        strategy = _plan_path(entities)
    elif intent == "comparison":
        strategy = _plan_comparison(entities)
    elif intent == "expansion":
        # Expansion requires web search (Phase 3)
        strategy = {
            "retrieval_type": "none",
            "message": "This query requires web search, which will be implemented in Phase 3.",
        }
    else:
        strategy = {
            "retrieval_type": "none",
            "error": f"Unknown intent: {intent}",
        }

    # Decide whether to add vector search
    strategy = _maybe_add_vector_search(strategy, intent, entities, state.get("user_query", ""))

    state["search_strategy"] = strategy
    return state


def _plan_lookup(entities: list[str]) -> dict:
    """Plan lookup query for a single entity."""
    if not entities:
        return {
            "retrieval_type": "graph_only",
            "cypher_template": None,
            "parameters": {},
            "error": "No entities found for lookup",
        }

    # Use first entity
    entity = entities[0]

    # Determine entity type based on heuristics
    entity_lower = entity.lower()

    # Check if it's a known principle
    principles = ["perception", "memory", "planning", "reasoning", "tool use",
                  "reflection", "grounding", "learning", "multi-agent", "guardrails", "tracing"]
    if any(p in entity_lower for p in principles):
        template_key = "lookup_principle"
    # Check if it's likely an implementation
    elif any(impl in entity_lower for impl in ["langchain", "crewai", "autogen", "langgraph", "semantic kernel"]):
        template_key = "lookup_implementation"
    # Default to method lookup
    else:
        template_key = "lookup_method"

    return {
        "retrieval_type": "graph_only",
        "cypher_template": CYPHER_TEMPLATES[template_key],
        "parameters": {"entity": entity},
        "template_key": template_key,
    }


def _plan_path(entities: list[str]) -> dict:
    """Plan path query for relationship exploration."""
    if not entities:
        return {
            "retrieval_type": "graph_only",
            "cypher_template": None,
            "parameters": {},
            "error": "No entities found for path query",
        }

    entity = entities[0]
    entity_lower = entity.lower()

    # Determine path direction based on entity type
    principles = ["perception", "memory", "planning", "reasoning", "tool use",
                  "reflection", "grounding", "learning", "multi-agent", "guardrails", "tracing"]
    implementations = ["langchain", "crewai", "autogen", "langgraph", "semantic kernel"]

    if any(p in entity_lower for p in principles):
        # Principle → Methods → Implementations
        template_key = "path_principle_to_methods"
    elif any(impl in entity_lower for impl in implementations):
        # Implementation → Methods → Principles
        template_key = "path_implementation_to_principles"
    else:
        # Assume method → Implementations
        template_key = "path_method_to_implementations"

    return {
        "retrieval_type": "graph_only",
        "cypher_template": CYPHER_TEMPLATES[template_key],
        "parameters": {"entity": entity},
        "template_key": template_key,
    }


def _plan_comparison(entities: list[str]) -> dict:
    """Plan comparison query for two entities."""
    if len(entities) < 2:
        return {
            "retrieval_type": "graph_only",
            "cypher_template": None,
            "parameters": {},
            "error": "Comparison requires at least 2 entities",
        }

    return {
        "retrieval_type": "graph_only",
        "cypher_template": CYPHER_TEMPLATES["comparison"],
        "parameters": {
            "entity1": entities[0],
            "entity2": entities[1],
        },
        "template_key": "comparison",
    }


def _maybe_add_vector_search(
    strategy: dict, intent: str, entities: list[str], user_query: str,
) -> dict:
    """Decide whether to augment the strategy with vector search.

    Rules:
    - expansion intent → vector_first (graph has nothing, try semantics)
    - no cypher template (failed match) → vector_first
    - lookup/path with entities → hybrid (graph + vector)
    - otherwise → leave as graph_only
    """
    retrieval_type = strategy.get("retrieval_type", "graph_only")

    # Check if vector store is available
    try:
        from src.retrieval.vector_store import get_vector_store
        store = get_vector_store()
        if not store.is_available:
            return strategy
    except Exception:
        return strategy

    vector_query = user_query or " ".join(entities or [])

    if intent == "expansion":
        strategy["retrieval_type"] = "vector_first"
        strategy["vector_query"] = vector_query
        print(f"[Search Planner] Strategy: vector_first (expansion intent)")
    elif retrieval_type == "none" or (retrieval_type == "graph_only" and not strategy.get("cypher_template")):
        # No valid Cypher template — fall back to vector search
        strategy["retrieval_type"] = "vector_first"
        strategy["vector_query"] = vector_query
        print(f"[Search Planner] Strategy: vector_first (no Cypher template)")
    elif intent in ("lookup", "path") and strategy.get("cypher_template"):
        strategy["retrieval_type"] = "hybrid"
        strategy["vector_query"] = vector_query
        print(f"[Search Planner] Strategy: hybrid (graph + vector)")

    return strategy
