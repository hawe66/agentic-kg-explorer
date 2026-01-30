"""Answer synthesis node for generating natural language responses."""

from ..providers.router import get_provider

from ..state import AgentState


SYNTHESIS_PROMPT = """You are a helpful assistant that answers questions about Agentic AI using a knowledge graph.

The knowledge graph contains:
- **Principles** (11 core capabilities): Perception, Memory, Planning, Reasoning, Tool Use, Reflection, Grounding, Learning, Multi-Agent, Guardrails, Tracing
- **Methods** (research techniques like ReAct, Chain-of-Thought, RAG)
- **Implementations** (frameworks like LangChain, CrewAI, AutoGen)
- **Standards** (like MCP, Agent-to-Agent, OpenTelemetry)

User Question: {query}

Query Intent: {intent}

Knowledge Graph Results:
{kg_results}

Based on the knowledge graph results above, provide a clear, concise answer to the user's question.

Guidelines:
1. If results are empty or insufficient, say "I couldn't find information about that in the knowledge graph."
2. Structure your answer clearly (use numbered lists or bullet points when appropriate)
3. Mention specific support levels when discussing implementations (e.g., "core support", "first-class")
4. If comparing entities, highlight both similarities and differences
5. Keep the answer focused and relevant to the question
6. Be factual - only use information from the provided results

Answer:"""


def synthesize_answer(state: AgentState) -> AgentState:
    """Generate natural language answer from knowledge graph results.

    Args:
        state: Current agent state with kg_results

    Returns:
        Updated state with answer, sources, and confidence
    """
    query = state.get("user_query")
    intent = state.get("intent")
    kg_results = state.get("kg_results", [])

    # Handle error cases only if no results available
    if state.get("error") and not kg_results:
        state["answer"] = f"I encountered an error: {state['error']}"
        state["sources"] = []
        state["confidence"] = 0.0
        return state

    # Handle expansion intent (web search not yet implemented)
    if intent == "expansion":
        state["answer"] = (
            "This question requires information beyond the current knowledge graph. "
            "Web search expansion will be available in Phase 3."
        )
        state["sources"] = []
        state["confidence"] = 0.0
        return state

    # Handle empty results
    if not kg_results:
        state["answer"] = "I couldn't find information about that in the knowledge graph."
        state["sources"] = []
        state["confidence"] = 0.1
        return state

    print(f"[Synthesizer] Synthesizing answer from {len(kg_results)} results")

    provider = get_provider()
    if provider is None:
        state["answer"] = _simple_format_results(kg_results, intent)
        state["sources"] = _extract_sources(kg_results)
        state["confidence"] = 0.5
        return state

    try:
        formatted_results = _format_results_for_llm(kg_results)

        answer = provider.generate(
            SYNTHESIS_PROMPT.format(
                query=query,
                intent=intent,
                kg_results=formatted_results,
            ),
            max_tokens=provider.max_synthesize_tokens,
        )

        # Extract sources from results
        sources = _extract_sources(kg_results)

        # Calculate confidence based on result count and intent match
        confidence = _calculate_confidence(kg_results, intent)

        state["answer"] = answer
        state["sources"] = sources
        state["confidence"] = confidence

        print(f"[Synthesizer] Generated answer with confidence: {confidence:.2f}")

    except Exception as e:
        print(f"[Synthesizer] Error: {e}")
        # Fallback to simple formatting
        state["answer"] = _simple_format_results(kg_results, intent)
        state["sources"] = _extract_sources(kg_results)
        state["confidence"] = 0.5

    return state


def _format_results_for_llm(results: list[dict]) -> str:
    """Format knowledge graph results as readable text for LLM."""
    if not results:
        return "No results found."

    formatted = []
    for i, record in enumerate(results, 1):
        formatted.append(f"Result {i}:")
        for key, value in record.items():
            if isinstance(value, dict):
                # Node or Relationship
                if "labels" in value:
                    # Node
                    labels = ", ".join(value["labels"])
                    props = value.get("properties", {})
                    formatted.append(f"  {key} ({labels}): {props}")
                elif "type" in value:
                    # Relationship
                    rel_type = value["type"]
                    props = value.get("properties", {})
                    formatted.append(f"  {key} [{rel_type}]: {props}")
            elif isinstance(value, list):
                formatted.append(f"  {key}: {value}")
            else:
                formatted.append(f"  {key}: {value}")
        formatted.append("")  # blank line between results

    return "\n".join(formatted)


def _simple_format_results(results: list[dict], intent: str) -> str:
    """Simple formatting without LLM (fallback)."""
    if not results:
        return "No results found in the knowledge graph."

    # Extract key information
    answer_parts = []

    for record in results:
        for key, value in record.items():
            if isinstance(value, dict) and "properties" in value:
                props = value["properties"]
                name = props.get("name", props.get("id", "Unknown"))
                desc = props.get("description", "")
                if desc:
                    answer_parts.append(f"- **{name}**: {desc}")
                else:
                    answer_parts.append(f"- **{name}**")

    if answer_parts:
        return "Here's what I found:\n\n" + "\n".join(answer_parts[:10])  # Limit to 10 items
    else:
        return f"Found {len(results)} results, but couldn't format them properly."


def _extract_sources(results: list[dict]) -> list[dict]:
    """Extract source nodes from results for citation."""
    sources = []
    seen_ids = set()

    for record in results:
        for key, value in record.items():
            if isinstance(value, dict) and "properties" in value:
                props = value["properties"]
                node_id = props.get("id")
                if node_id and node_id not in seen_ids:
                    labels = value.get("labels", [])
                    node_type = labels[0] if labels else "Unknown"
                    sources.append({
                        "type": node_type,
                        "id": node_id,
                        "name": props.get("name", node_id),
                    })
                    seen_ids.add(node_id)

    return sources


def _calculate_confidence(results: list[dict], intent: str) -> float:
    """Calculate confidence score based on results and intent."""
    if not results:
        return 0.0

    # Base confidence on result count
    result_count = len(results)
    if result_count == 0:
        return 0.0
    elif result_count >= 5:
        base_confidence = 0.9
    elif result_count >= 3:
        base_confidence = 0.8
    elif result_count >= 1:
        base_confidence = 0.7
    else:
        base_confidence = 0.5

    # Adjust based on intent
    # Lookup and path queries are more reliable than comparisons
    if intent in ["lookup", "path"]:
        confidence = base_confidence
    elif intent == "comparison":
        confidence = base_confidence * 0.9
    else:
        confidence = base_confidence * 0.8

    return round(confidence, 2)
