"""Search planning node for generating Cypher query strategies."""

import yaml
from pathlib import Path
from typing import Optional

from ..state import AgentState


# Load configuration from YAML
_CONFIG_PATH = Path("config/cypher_templates.yaml")
_config: Optional[dict] = None


def _load_config() -> dict:
    """Load Cypher templates configuration from YAML."""
    global _config
    if _config is not None:
        return _config

    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    else:
        # Fallback to empty config
        _config = {"templates": {}, "entity_patterns": {}, "default_templates": {}}
        print(f"[Search Planner] Warning: {_CONFIG_PATH} not found, using empty config")

    return _config


def _detect_entity_type(entity: str) -> str:
    """Detect entity type based on patterns from config."""
    config = _load_config()
    patterns = config.get("entity_patterns", {})
    entity_lower = entity.lower()

    for entity_type, type_patterns in patterns.items():
        for pattern in type_patterns:
            if pattern.lower() in entity_lower:
                return entity_type

    return "Method"  # Default fallback


def _select_template(intent: str, entity_types: list[str]) -> Optional[dict]:
    """Select appropriate Cypher template based on intent and entity types."""
    config = _load_config()
    templates = config.get("templates", {})
    defaults = config.get("default_templates", {})

    # Try to find exact match for intent + entity types
    for template_key, template in templates.items():
        template_intents = template.get("intent", [])
        if isinstance(template_intents, str):
            template_intents = [template_intents]

        if intent not in template_intents:
            continue

        template_entity_types = template.get("entity_types", [])

        # Match entity types (order matters for comparison)
        if len(entity_types) == len(template_entity_types):
            if all(et in template_entity_types for et in entity_types):
                return {"key": template_key, **template}

    # Try default template for intent
    if intent in defaults:
        default_key = defaults[intent]
        if default_key in templates:
            return {"key": default_key, **templates[default_key]}

    return None


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

    # Handle intents that don't need graph queries
    if intent == "out_of_scope":
        state["search_strategy"] = {
            "retrieval_type": "none",
            "message": "Query is out of scope for this knowledge graph.",
        }
        return state

    if intent == "expansion":
        strategy = {
            "retrieval_type": "vector_first",
            "cypher_template": None,
            "parameters": {},
            "message": "Expansion query - will use vector + web search.",
        }
        strategy = _maybe_add_vector_search(strategy, intent, entities, state.get("user_query", ""))
        state["search_strategy"] = strategy
        return state

    # Detect entity types
    entity_types = [_detect_entity_type(e) for e in entities] if entities else []

    # Select template based on intent and entity types
    template = _select_template(intent, entity_types)

    if template:
        # Build parameters from entities
        params = {}
        param_names = template.get("params", [])
        for i, param_name in enumerate(param_names):
            if i < len(entities):
                params[param_name] = entities[i]

        strategy = {
            "retrieval_type": "graph_only",
            "cypher_template": template.get("cypher"),
            "parameters": params,
            "template_key": template.get("key"),
        }
    else:
        # No matching template found
        strategy = {
            "retrieval_type": "graph_only",
            "cypher_template": None,
            "parameters": {},
            "error": f"No template found for intent={intent}, entity_types={entity_types}",
        }

    # Decide whether to add vector search
    strategy = _maybe_add_vector_search(strategy, intent, entities, state.get("user_query", ""))

    state["search_strategy"] = strategy
    return state


def _maybe_add_vector_search(
    strategy: dict, intent: str, entities: list[str], user_query: str,
) -> dict:
    """Decide whether to augment the strategy with vector search.

    Rules:
    - expansion intent → vector_first (graph has nothing, try semantics)
    - no cypher template (failed match) → vector_first
    - lookup/path/exploration with entities → hybrid (graph + vector)
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
    elif intent in ("lookup", "path", "exploration", "path_trace") and strategy.get("cypher_template"):
        strategy["retrieval_type"] = "hybrid"
        strategy["vector_query"] = vector_query
        print(f"[Search Planner] Strategy: hybrid (graph + vector)")

    return strategy
