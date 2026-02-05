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
{vector_section}
{web_section}
Based on the results above, provide a clear, concise answer to the user's question.

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
    entities = state.get("entities") or []
    kg_results = state.get("kg_results", [])
    vector_results = state.get("vector_results") or []
    web_results = state.get("web_results") or []

    # Handle out_of_scope intent early
    if intent == "out_of_scope":
        state["answer"] = "I'm sorry, but this question is outside my area of expertise. I specialize in Agentic AI topics including principles, methods, implementations, and standards. Could you ask something related to AI agents?"
        state["sources"] = []
        state["confidence"] = 0.0
        return state

    has_any_results = bool(kg_results) or bool(vector_results) or bool(web_results)

    # Handle error cases only if no results available
    if state.get("error") and not has_any_results:
        state["answer"] = f"I encountered an error: {state['error']}"
        state["sources"] = []
        state["confidence"] = 0.0
        return state

    # Handle empty results (no KG, no vector, no web)
    if not has_any_results:
        state["answer"] = "I couldn't find information about that in the knowledge graph or web search."
        state["sources"] = []
        state["confidence"] = 0.1
        return state

    print(f"[Synthesizer] Synthesizing answer from {len(kg_results)} graph + {len(vector_results)} vector + {len(web_results)} web results")

    provider = get_provider()
    if provider is None:
        state["answer"] = _simple_format_results(kg_results, intent)
        state["sources"] = _extract_sources(kg_results)
        state["confidence"] = 0.5
        return state

    try:
        formatted_results = _format_results_for_llm(kg_results)
        vector_section = _format_vector_results(vector_results)
        web_section = _format_web_results(web_results)

        answer = provider.generate(
            SYNTHESIS_PROMPT.format(
                query=query,
                intent=intent,
                kg_results=formatted_results,
                vector_section=vector_section,
                web_section=web_section,
            ),
            max_tokens=provider.max_synthesize_tokens,
        )

        sources = _extract_sources(kg_results) + _extract_web_sources(web_results)
        confidence = _calculate_confidence(
            kg_results, intent, vector_results, web_results, entities
        )

        state["answer"] = answer
        state["sources"] = sources
        state["confidence"] = confidence

        print(f"[Synthesizer] Generated answer with confidence: {confidence:.2f}")

    except Exception as e:
        print(f"[Synthesizer] Error: {e}")
        state["answer"] = _simple_format_results(kg_results, intent)
        state["sources"] = _extract_sources(kg_results) + _extract_web_sources(web_results)
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


def _extract_web_sources(web_results: list[dict]) -> list[dict]:
    """Extract web search results as sources for citation."""
    if not web_results:
        return []

    sources = []
    for r in web_results:
        url = r.get("url", "")
        if url:
            sources.append({
                "type": "Web",
                "id": url,
                "name": r.get("title", url),
            })
    return sources


def _format_vector_results(vector_results: list[dict]) -> str:
    """Format vector search results for inclusion in the LLM prompt."""
    if not vector_results:
        return ""

    lines = ["\nSemantic Search Results (by similarity):"]
    for r in vector_results:
        score = r.get("score", 0)
        node_id = r.get("node_id") or r.get("source_id", "?")
        label = r.get("node_label", "?")
        title = r.get("title", "")
        text = r.get("text", "")
        # Truncate long texts
        if len(text) > 300:
            text = text[:300] + "..."
        display = title if title else node_id
        lines.append(f"- {display} ({label}, score: {score:.2f}):")
        lines.append(f"  {text}")
    return "\n".join(lines)


def _format_web_results(web_results: list[dict]) -> str:
    """Format web search results for LLM prompt."""
    if not web_results:
        return ""

    lines = ["\nWeb Search Results:"]
    for r in web_results:
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = r.get("content", "")[:300]  # truncate
        score = r.get("score", 0)
        lines.append(f"- [{title}]({url}) (score: {score:.2f})")
        lines.append(f"  {content}...")
    return "\n".join(lines)


def _calculate_confidence(
    results: list[dict],
    intent: str,
    vector_results: list[dict] | None = None,
    web_results: list[dict] | None = None,
    entities: list[str] | None = None,
) -> float:
    """Calculate multi-dimensional confidence score.

    Dimensions (per comments.md P0):
    1. Entity matching (0.3 weight): Did we find the entities user asked about?
    2. Intent fulfillment (0.3 weight): Does result structure match intent?
    3. Data completeness (0.2 weight): Are key fields populated?
    4. Vector similarity (0.2 weight): How semantically relevant are results?
    """
    if not results and not vector_results and not web_results:
        return 0.0

    entities = entities or []
    scores = []

    # 1. Entity Matching Score (weight: 0.3)
    entity_score = _calc_entity_match_score(entities, results, vector_results)
    scores.append(("entity_match", entity_score, 0.3))

    # 2. Intent Fulfillment Score (weight: 0.3)
    intent_score = _calc_intent_fulfillment_score(intent, results, vector_results, web_results)
    scores.append(("intent_fulfillment", intent_score, 0.3))

    # 3. Data Completeness Score (weight: 0.2)
    completeness_score = _calc_completeness_score(results)
    scores.append(("completeness", completeness_score, 0.2))

    # 4. Vector Similarity Score (weight: 0.2)
    vector_score = _calc_vector_similarity_score(vector_results)
    scores.append(("vector_similarity", vector_score, 0.2))

    # Weighted average
    total = sum(score * weight for _, score, weight in scores)

    return round(total, 2)


def _calc_entity_match_score(
    entities: list[str],
    kg_results: list[dict],
    vector_results: list[dict] | None,
) -> float:
    """Calculate how many requested entities were found in results."""
    if not entities:
        # No specific entities requested; neutral score
        return 0.5

    # Extract all entity IDs/names from results
    found_ids = set()
    found_names = set()

    for record in (kg_results or []):
        for value in record.values():
            if isinstance(value, dict) and "properties" in value:
                props = value["properties"]
                if props.get("id"):
                    found_ids.add(props["id"].lower())
                if props.get("name"):
                    found_names.add(props["name"].lower())

    for vr in (vector_results or []):
        if vr.get("node_id"):
            found_ids.add(vr["node_id"].lower())
        if vr.get("title"):
            found_names.add(vr["title"].lower())

    # Count matches
    matched = 0
    for entity in entities:
        entity_lower = entity.lower()
        if entity_lower in found_ids or entity_lower in found_names:
            matched += 1
        # Partial match check (e.g., "react" in "m:react")
        elif any(entity_lower in fid for fid in found_ids):
            matched += 0.5
        elif any(entity_lower in fname for fname in found_names):
            matched += 0.5

    return min(matched / len(entities), 1.0)


def _calc_intent_fulfillment_score(
    intent: str,
    kg_results: list[dict],
    vector_results: list[dict] | None,
    web_results: list[dict] | None,
) -> float:
    """Check if result structure matches what the intent requires."""
    kg_count = len(kg_results) if kg_results else 0
    vector_count = len(vector_results) if vector_results else 0
    web_count = len(web_results) if web_results else 0
    total_count = kg_count + vector_count

    if intent == "lookup":
        # Lookup: need at least 1 result with good detail
        if kg_count >= 1:
            return 1.0
        elif vector_count >= 1:
            return 0.8
        elif web_count >= 1:
            return 0.5
        return 0.0

    elif intent == "path":
        # Path: need results showing relationships
        if kg_count >= 2:  # At least start and end nodes
            return 1.0
        elif kg_count >= 1:
            return 0.7
        elif vector_count >= 1:
            return 0.5
        return 0.0

    elif intent == "comparison":
        # Comparison: need at least 2 distinct entities to compare
        distinct_entities = _count_distinct_entities(kg_results)
        if distinct_entities >= 2:
            return 1.0
        elif distinct_entities == 1 and (vector_count > 0 or web_count > 0):
            return 0.6
        elif distinct_entities == 1:
            return 0.4
        return 0.0

    elif intent == "expansion":
        # Expansion: web results are expected and valid
        if web_count >= 1:
            return 0.9
        elif kg_count >= 1 or vector_count >= 1:
            return 0.7  # Found in KG after all
        return 0.0

    elif intent == "out_of_scope":
        # Out of scope: we shouldn't have relevant results
        return 0.0  # Low confidence by design

    return 0.5  # Unknown intent


def _count_distinct_entities(kg_results: list[dict]) -> int:
    """Count distinct entity IDs in KG results."""
    entity_ids = set()
    for record in (kg_results or []):
        for value in record.values():
            if isinstance(value, dict) and "properties" in value:
                eid = value["properties"].get("id")
                if eid:
                    entity_ids.add(eid)
    return len(entity_ids)


def _calc_completeness_score(kg_results: list[dict]) -> float:
    """Check if key fields are populated in results."""
    if not kg_results:
        return 0.5  # Neutral when no KG results

    total_fields = 0
    filled_fields = 0

    key_fields = ["name", "description", "id"]

    for record in kg_results:
        for value in record.values():
            if isinstance(value, dict) and "properties" in value:
                props = value["properties"]
                for field in key_fields:
                    total_fields += 1
                    if props.get(field):
                        filled_fields += 1

    if total_fields == 0:
        return 0.5

    return filled_fields / total_fields


def _calc_vector_similarity_score(vector_results: list[dict] | None) -> float:
    """Calculate average vector similarity score."""
    if not vector_results:
        return 0.5  # Neutral when no vector results

    scores = [r.get("score", 0) for r in vector_results if r.get("score")]
    if not scores:
        return 0.5

    return sum(scores) / len(scores)
