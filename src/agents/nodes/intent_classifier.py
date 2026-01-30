"""Intent classification node for identifying query type."""

import re
from typing import Literal

from ..providers.router import get_provider

from ..state import AgentState


INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a knowledge graph about Agentic AI.

The knowledge graph contains:
- **Principles** (11 core capabilities): Perception, Memory, Planning, Reasoning, Tool Use, Reflection, Grounding, Learning, Multi-Agent, Guardrails, Tracing
- **Methods** (research techniques): ReAct, Chain-of-Thought, RAG, etc.
- **Implementations** (frameworks/services): LangChain, CrewAI, AutoGen, etc.
- **Standards**: MCP, Agent-to-Agent, OpenTelemetry

Classify the user query into ONE of these intents:

1. **lookup** - Single concept lookup
   Examples: "What is ReAct?", "Tell me about LangChain", "Explain Memory principle"

2. **path** - Relationship exploration between concepts
   Examples: "What methods address Planning?", "Which frameworks implement ReAct?", "How does AutoGen support Tool Use?"

3. **comparison** - Compare multiple concepts
   Examples: "CrewAI vs AutoGen", "Difference between CoT and ReAct", "Compare LangChain and CrewAI"

4. **expansion** - Information likely NOT in the graph (requires web search)
   Examples: "Latest agent frameworks in 2025", "New research on agentic AI", "Future of AI agents"

Additionally, extract key entities mentioned in the query.

User Query: {query}

Respond in this exact format:
INTENT: <lookup|path|comparison|expansion>
ENTITIES: <comma-separated list of entities>
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
        content = provider.generate(
            INTENT_CLASSIFICATION_PROMPT.format(query=query),
            max_tokens=provider.max_classify_tokens,
        )

        intent = _extract_intent(content)
        entities = _extract_entities(content)

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


def _extract_intent(content: str) -> Literal["lookup", "path", "comparison", "expansion"]:
    """Extract intent from LLM response."""
    match = re.search(r"INTENT:\s*(lookup|path|comparison|expansion)", content, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return "lookup"  # default fallback


def _extract_entities(content: str) -> list[str]:
    """Extract entities from LLM response."""
    match = re.search(r"ENTITIES:\s*(.+)", content, re.IGNORECASE)
    if match:
        entities_str = match.group(1).strip()
        # Split by comma and clean up
        entities = [e.strip() for e in entities_str.split(",") if e.strip()]
        return entities
    return []


def _fallback_intent_classification(query: str) -> Literal["lookup", "path", "comparison", "expansion"]:
    """Simple heuristic-based intent classification as fallback."""
    query_lower = query.lower()

    # Comparison keywords
    if any(kw in query_lower for kw in ["vs", "versus", "compare", "difference between"]):
        return "comparison"

    # Path/relationship keywords
    if any(kw in query_lower for kw in ["implement", "support", "address", "method for", "framework for"]):
        return "path"

    # Expansion keywords
    if any(kw in query_lower for kw in ["latest", "new", "recent", "2025", "2026", "future"]):
        return "expansion"

    # Default to lookup
    return "lookup"


def _fallback_entity_extraction(query: str) -> list[str]:
    """Simple entity extraction as fallback."""
    # Known entities (this could be expanded or replaced with NER)
    known_entities = [
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
    for entity in known_entities:
        if entity.lower() in query.lower():
            entities.append(entity)

    return entities
