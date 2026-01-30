"""LangGraph pipeline for knowledge graph exploration."""

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    classify_intent,
    plan_search,
    retrieve_from_graph,
    synthesize_answer,
)


def create_agent_graph() -> StateGraph:
    """Create the LangGraph pipeline for KG exploration.

    The pipeline flows as follows:
    User Query → Intent Classification → Search Planning → Graph Retrieval → Answer Synthesis

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("plan_search", plan_search)
    workflow.add_node("retrieve_from_graph", retrieve_from_graph)
    workflow.add_node("synthesize_answer", synthesize_answer)

    # Define edges (linear flow for Phase 2)
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "plan_search")
    workflow.add_edge("plan_search", "retrieve_from_graph")
    workflow.add_edge("retrieve_from_graph", "synthesize_answer")
    workflow.add_edge("synthesize_answer", END)

    # Compile graph
    return workflow.compile()


def run_agent(query: str) -> AgentState:
    """Run the agent pipeline on a user query.

    Args:
        query: User question about the knowledge graph

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
        "error": None,
    }

    # Run graph
    print(f"\n{'='*60}")
    print(f"Processing query: {query}")
    print(f"{'='*60}\n")

    final_state = graph.invoke(initial_state)

    return final_state


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
