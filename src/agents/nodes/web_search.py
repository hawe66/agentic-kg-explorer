"""Web search node using Tavily API."""

import os
from ..state import AgentState


def web_search(state: AgentState) -> AgentState:
    """Execute web search when KG has no results or intent is expansion.

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

        state["web_results"] = results
        state["web_query"] = query
        print(f"[Web Search] Found {len(results)} results")

    except Exception as e:
        print(f"[Web Search] Error: {e}")
        state["web_results"] = []
        state["web_query"] = query

    return state
