"""LangGraph pipeline for knowledge graph exploration."""

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    classify_intent,
    plan_search,
    retrieve_from_graph,
    web_search,
    synthesize_answer,
)


def _should_web_search(state: AgentState) -> str:
    """Decide whether to run web search after graph retrieval.

    Returns "web_search" if:
    - intent is "expansion", OR
    - both kg_results and vector_results are empty

    Otherwise returns "synthesize" to skip web search.
    """
    intent = state.get("intent")
    kg_results = state.get("kg_results") or []
    vector_results = state.get("vector_results") or []

    has_results = bool(kg_results) or bool(vector_results)

    if intent == "expansion" or not has_results:
        return "web_search"
    return "synthesize"


def create_agent_graph() -> StateGraph:
    """Create the LangGraph pipeline for KG exploration.

    The pipeline flows as follows:
    User Query → Intent Classification → Search Planning → Graph Retrieval
                                                               ↓
                                                    [conditional: has results?]
                                                         ↓            ↓
                                                       YES           NO (or expansion)
                                                         ↓            ↓
                                                       skip      Web Search
                                                         ↓            ↓
                                                         └────────────┘
                                                               ↓
                                                        Answer Synthesis

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("plan_search", plan_search)
    workflow.add_node("retrieve_from_graph", retrieve_from_graph)
    workflow.add_node("web_search", web_search)
    workflow.add_node("synthesize_answer", synthesize_answer)

    # Define edges
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "plan_search")
    workflow.add_edge("plan_search", "retrieve_from_graph")

    # Conditional: after retrieval → web_search OR synthesize
    workflow.add_conditional_edges(
        "retrieve_from_graph",
        _should_web_search,
        {
            "web_search": "web_search",
            "synthesize": "synthesize_answer",
        },
    )

    # web_search always goes to synthesize
    workflow.add_edge("web_search", "synthesize_answer")
    workflow.add_edge("synthesize_answer", END)

    # Compile graph
    return workflow.compile()


def run_agent(query: str, evaluate: bool = False) -> AgentState:
    """Run the agent pipeline on a user query.

    Args:
        query: User question about the knowledge graph
        evaluate: If True, run critic evaluation after pipeline (default: False)

    Returns:
        Final state with answer and sources
    """
    # Create graph
    graph = create_agent_graph()

    # Initialize state
    initial_state: AgentState = {
        "user_query": query,
        "intent": None,
        "entities": None,
        "search_strategy": None,
        "kg_results": None,
        "cypher_executed": None,
        "answer": None,
        "sources": None,
        "confidence": None,
        "vector_results": None,
        "web_results": None,
        "web_query": None,
        "error": None,
    }

    # Run graph
    print(f"\n{'='*60}")
    print(f"Processing query: {query}")
    print(f"{'='*60}\n")

    final_state = graph.invoke(initial_state)

    # Post-pipeline evaluation (if enabled)
    if evaluate:
        _run_evaluation(final_state)

    return final_state


def _run_evaluation(state: AgentState) -> None:
    """Run critic evaluation on pipeline results (async-friendly hook).

    Args:
        state: Final pipeline state to evaluate.
    """
    try:
        from src.critic.evaluator import get_evaluator

        evaluator = get_evaluator()
        evaluations = evaluator.evaluate_pipeline(state)

        if evaluations:
            print(f"\n[Critic] Evaluated {len(evaluations)} agents:")
            for ev in evaluations:
                print(f"  - {ev.agent_name}: {ev.composite_score:.2f}")
                if ev.feedback:
                    print(f"    Feedback: {ev.feedback[:100]}...")

                # Save to Neo4j (optional)
                # evaluator.save_to_neo4j(ev)

    except Exception as e:
        print(f"[Critic] Evaluation failed: {e}")


if __name__ == "__main__":
    # Example usage
    test_queries = [
        "What is ReAct?",
        "What methods address Planning principle?",
        "Which frameworks implement ReAct?",
        "Compare LangChain and CrewAI",
    ]

    for query in test_queries:
        result = run_agent(query)
        print(f"\nQuery: {query}")
        print(f"Intent: {result['intent']}")
        print(f"Answer: {result['answer']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Sources: {len(result.get('sources', []))} sources")
        print(f"\n{'-'*60}\n")
