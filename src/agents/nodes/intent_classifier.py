"""Intent classification node for identifying query type."""

import json
import re
import yaml
from pathlib import Path
from typing import Literal

from ..providers.router import get_provider

from ..state import AgentState


# Load configs
ENTITY_CATALOG = None
ENTITY_CATALOG_PATH = Path("data/entity_catalog.json")
INTENTS_CONFIG = None
INTENTS_CONFIG_PATH = Path("config/intents.yaml")


def _load_entity_catalog() -> dict | None:
    """Load entity catalog from JSON file."""
    global ENTITY_CATALOG
    if ENTITY_CATALOG is not None:
        return ENTITY_CATALOG

    if ENTITY_CATALOG_PATH.exists():
        try:
            with open(ENTITY_CATALOG_PATH, "r", encoding="utf-8") as f:
                ENTITY_CATALOG = json.load(f)
            return ENTITY_CATALOG
        except Exception as e:
            print(f"[Intent Classifier] Failed to load entity catalog: {e}")
    return None


def _load_intents_config() -> dict | None:
    """Load intents configuration from YAML file."""
    global INTENTS_CONFIG
    if INTENTS_CONFIG is not None:
        return INTENTS_CONFIG

    if INTENTS_CONFIG_PATH.exists():
        try:
            with open(INTENTS_CONFIG_PATH, "r", encoding="utf-8") as f:
                INTENTS_CONFIG = yaml.safe_load(f)
            return INTENTS_CONFIG
        except Exception as e:
            print(f"[Intent Classifier] Failed to load intents config: {e}")
    return None


def _build_entity_context() -> str:
    """Build entity context string for the prompt."""
    catalog = _load_entity_catalog()
    if not catalog:
        return """- **Principles** (11 core capabilities): Perception, Memory, Planning, Reasoning, Tool Use, Reflection, Grounding, Learning, Multi-Agent, Guardrails, Tracing
- **Methods** (research techniques): ReAct, Chain-of-Thought, RAG, etc.
- **Implementations** (frameworks/services): LangChain, CrewAI, AutoGen, etc.
- **Standards**: MCP, Agent-to-Agent, OpenTelemetry"""

    lines = []

    # Principles
    principle_names = [p["name"] for p in catalog.get("principles", [])]
    lines.append(f"- **Principles** ({len(principle_names)}): {', '.join(principle_names)}")

    # Methods (show first 20 with families)
    methods = catalog.get("methods", [])
    method_names = [m["name"] for m in methods[:20]]
    lines.append(f"- **Methods** ({len(methods)} total, examples): {', '.join(method_names)}")

    # Implementations
    impls = catalog.get("implementations", [])
    impl_names = [i["name"] for i in impls]
    lines.append(f"- **Implementations** ({len(impls)}): {', '.join(impl_names)}")

    # Standards
    standards = catalog.get("standards", [])
    std_names = [s["name"] for s in standards]
    lines.append(f"- **Standards** ({len(standards)}): {', '.join(std_names)}")

    # Aliases hint
    aliases = catalog.get("aliases", {})
    if aliases:
        alias_examples = ["CoT=Chain-of-Thought", "RAG=Retrieval-Augmented Generation", "OTel=OpenTelemetry"]
        lines.append(f"\nCommon aliases: {', '.join(alias_examples)}")

    return "\n".join(lines)


def _build_intent_list() -> tuple[str, list[str]]:
    """Build intent list string for the prompt from config."""
    config = _load_intents_config()

    # Default intents if config not available
    default_intents = ["lookup", "path", "comparison", "expansion", "out_of_scope"]

    if not config:
        return """1. **lookup** - Single concept lookup
   Examples: "What is ReAct?", "Tell me about LangChain"

2. **path** - Relationship exploration between concepts
   Examples: "What methods address Planning?", "Which frameworks implement ReAct?"

3. **comparison** - Compare multiple concepts
   Examples: "CrewAI vs AutoGen", "Difference between CoT and ReAct"

4. **expansion** - Information likely NOT in the graph but WITHIN the Agentic AI domain
   Examples: "Latest agent frameworks in 2025", "New research on agentic AI"

5. **out_of_scope** - Query is OUTSIDE the Agentic AI domain entirely
   Examples: "What's the weather?", "Who won the World Cup?"
""", default_intents

    intents = config.get("intents", {})
    lines = []
    intent_names = []

    for i, (intent_name, intent_data) in enumerate(intents.items(), 1):
        intent_names.append(intent_name)
        desc = intent_data.get("description", "")
        examples = intent_data.get("examples", [])[:2]  # Show max 2 examples
        examples_str = ", ".join(f'"{e}"' for e in examples)
        lines.append(f"{i}. **{intent_name}** - {desc}")
        if examples_str:
            lines.append(f"   Examples: {examples_str}")
        lines.append("")

    return "\n".join(lines), intent_names


INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a knowledge graph about Agentic AI.

The knowledge graph contains:
{entity_context}

Classify the user query into ONE of these intents:

{intent_list}
IMPORTANT:
- Extract entities using EXACT names from the knowledge graph when possible
- If the query mentions an entity not in the graph but is about Agentic AI, use "expansion"
- If the query is completely unrelated to AI/agents/ML, use "out_of_scope"

User Query: {query}

Respond in this exact format:
INTENT: <{intent_options}>
ENTITIES: <comma-separated list of entities, use exact names from KG when possible>
REASONING: <brief explanation>
"""


def classify_intent(state: AgentState) -> AgentState:
    """Classify user query intent and extract entities.

    Args:
        state: Current agent state with user_query

    Returns:
        Updated state with intent and entities
    """
    query = state["user_query"]

    provider = get_provider()
    if provider is None:
        state["intent"] = _fallback_intent_classification(query)
        state["entities"] = _fallback_entity_extraction(query)
        return state

    try:
        # Build prompt with dynamic entity context and intents from config
        entity_context = _build_entity_context()
        intent_list, intent_names = _build_intent_list()
        intent_options = "|".join(intent_names)

        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            entity_context=entity_context,
            intent_list=intent_list,
            intent_options=intent_options,
            query=query
        )

        content = provider.generate(
            prompt,
            max_tokens=provider.max_classify_tokens,
        )

        intent = _extract_intent(content, intent_names)
        entities = _extract_entities(content)

        # Normalize entities using catalog aliases
        entities = _normalize_entities(entities)

        state["intent"] = intent
        state["entities"] = entities

        print(f"[Intent Classifier] Intent: {intent}, Entities: {entities}")

    except Exception as exc:
        print(f"[Intent Classifier] Error type: {type(exc).__name__}")
        print(f"[Intent Classifier] Error message: {str(exc)}")
        import traceback

        print(f"[Intent Classifier] Traceback:\n{traceback.format_exc()}")
        state["intent"] = _fallback_intent_classification(query)
        state["entities"] = _fallback_entity_extraction(query)
        print(
            f"[Intent Classifier] Using fallback - Intent: {state['intent']}, Entities: {state['entities']}"
        )

    return state


def _normalize_entities(entities: list[str]) -> list[str]:
    """Normalize entity names using catalog aliases."""
    catalog = _load_entity_catalog()
    if not catalog:
        return entities

    aliases = catalog.get("aliases", {})
    normalized = []

    for entity in entities:
        entity_lower = entity.lower().strip()
        if entity_lower in aliases:
            # Return the canonical ID
            normalized.append(aliases[entity_lower])
        else:
            # Keep original
            normalized.append(entity)

    return normalized


def _extract_intent(content: str, valid_intents: list[str] | None = None) -> str:
    """Extract intent from LLM response."""
    if valid_intents is None:
        valid_intents = ["lookup", "path", "comparison", "expansion", "out_of_scope"]

    # Build regex pattern from valid intents
    pattern = r"INTENT:\s*(" + "|".join(valid_intents) + ")"
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return "lookup"  # default fallback


def _extract_entities(content: str) -> list[str]:
    """Extract entities from LLM response."""
    # Match ENTITIES line - use [ \t]* instead of \s* to avoid matching newlines
    match = re.search(r"ENTITIES:[ \t]*([^\n\r]*)", content, re.IGNORECASE)
    if match:
        entities_str = match.group(1).strip()
        # Handle "None", "N/A", empty cases
        if not entities_str or entities_str.lower() in ["none", "n/a", "-"]:
            return []
        # Split by comma and clean up
        entities = [e.strip() for e in entities_str.split(",") if e.strip()]
        return entities
    return []


def _fallback_intent_classification(query: str) -> str:
    """Simple heuristic-based intent classification as fallback."""
    query_lower = query.lower()

    # Out of scope keywords (completely unrelated to AI/agents)
    out_of_scope_keywords = [
        "weather", "cook", "recipe", "sport", "game", "movie", "music",
        "joke", "hello", "hi", "thanks", "bye", "world cup", "stock",
    ]
    if any(kw in query_lower for kw in out_of_scope_keywords):
        # Double-check it's not about AI
        ai_keywords = ["ai", "agent", "llm", "model", "neural", "machine learning", "ml"]
        if not any(ai_kw in query_lower for ai_kw in ai_keywords):
            return "out_of_scope"

    # Comparison keywords
    if any(kw in query_lower for kw in ["vs", "versus", "compare", "difference between"]):
        return "comparison"

    # Aggregation keywords
    if any(kw in query_lower for kw in ["how many", "count", "statistics", "distribution"]):
        return "aggregation"

    # Coverage check keywords
    if any(kw in query_lower for kw in ["missing", "orphan", "without paper", "coverage", "gap"]):
        return "coverage_check"

    # Definition keywords
    if any(kw in query_lower for kw in ["what is the relationship", "what are the 11", "schema", "explain the"]):
        return "definition"

    # Path/relationship keywords (exploration)
    if any(kw in query_lower for kw in ["implement", "support", "address", "method for", "framework for"]):
        return "exploration"

    # Path trace keywords
    if any(kw in query_lower for kw in ["connect", "path from", "trace", "how does.*relate"]):
        return "path_trace"

    # Expansion keywords
    if any(kw in query_lower for kw in ["latest", "new", "recent", "2025", "2026", "future"]):
        return "expansion"

    # Default to lookup
    return "lookup"


def _fallback_entity_extraction(query: str) -> list[str]:
    """Simple entity extraction as fallback using catalog or hardcoded list."""
    catalog = _load_entity_catalog()

    if catalog:
        # Use catalog for entity matching
        all_names = []
        for p in catalog.get("principles", []):
            all_names.append(p["name"])
        for m in catalog.get("methods", []):
            all_names.append(m["name"])
        for i in catalog.get("implementations", []):
            all_names.append(i["name"])
        for s in catalog.get("standards", []):
            all_names.append(s["name"])

        # Add aliases
        all_names.extend(catalog.get("aliases", {}).keys())
    else:
        # Fallback to hardcoded list
        all_names = [
            # Principles
            "Perception", "Memory", "Planning", "Reasoning", "Tool Use",
            "Reflection", "Grounding", "Learning", "Multi-Agent", "Guardrails", "Tracing",
            # Methods
            "ReAct", "Chain-of-Thought", "CoT", "RAG", "Self-Consistency",
            "Tree of Thoughts", "Plan-and-Execute", "LATS",
            # Implementations
            "LangChain", "CrewAI", "AutoGen", "LangGraph", "Semantic Kernel",
            # Standards
            "MCP", "Agent-to-Agent", "A2A", "OpenTelemetry", "OTel",
        ]

    entities = []
    query_lower = query.lower()
    for entity in all_names:
        if entity.lower() in query_lower:
            entities.append(entity)

    # Normalize using catalog aliases
    return _normalize_entities(entities) if catalog else entities
