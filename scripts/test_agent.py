"""Test script for LangGraph agent pipeline.

Usage:
    python scripts/test_agent.py
    python scripts/test_agent.py --query "What is ReAct?"
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents import run_agent


# Test queries covering different intents
TEST_QUERIES = [
    # Lookup queries
    "What is ReAct?",
    "Tell me about LangChain",
    "Explain the Planning principle",

    # Path queries
    "What methods address the Planning principle?",
    "Which frameworks implement ReAct?",
    "How does AutoGen support Tool Use?",
    "What principles does CrewAI address?",

    # Comparison queries
    "Compare LangChain and CrewAI",
    "What's the difference between ReAct and Chain-of-Thought?",

    # Expansion queries (will trigger Phase 3 message)
    "What are the latest agent frameworks in 2025?",
]


def test_single_query(query: str, verbose: bool = False):
    """Test a single query through the agent pipeline."""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")

    result = run_agent(query)

    print(f"\n[Results]")
    print(f"Intent: {result.get('intent')}")
    print(f"Entities: {result.get('entities')}")
    print(f"\nAnswer:\n{result.get('answer')}")
    print(f"\nConfidence: {result.get('confidence')}")

    sources = result.get('sources', [])
    if sources:
        print(f"\nSources ({len(sources)}):")
        for source in sources[:5]:  # Show first 5 sources
            print(f"  - {source['type']}: {source['name']} (ID: {source['id']})")
        if len(sources) > 5:
            print(f"  ... and {len(sources) - 5} more")

    if verbose and result.get('cypher_executed'):
        print(f"\nCypher Queries:")
        for cypher in result['cypher_executed']:
            print(f"  {cypher[:100]}...")

    if result.get('error'):
        print(f"\n[Error] {result['error']}")

    print(f"\n{'-'*80}\n")

    return result


def test_all_queries():
    """Run all test queries."""
    print(f"\n{'#'*80}")
    print("Testing LangGraph Agent Pipeline")
    print(f"{'#'*80}\n")

    results = []
    for query in TEST_QUERIES:
        result = test_single_query(query, verbose=False)
        results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}\n")

    total = len(results)
    errors = sum(1 for r in results if r.get('error'))
    high_confidence = sum(1 for r in results if r.get('confidence', 0) >= 0.7)

    print(f"Total queries: {total}")
    print(f"Successful: {total - errors}")
    print(f"Errors: {errors}")
    print(f"High confidence (≥0.7): {high_confidence}")

    # Intent distribution
    intent_counts = {}
    for r in results:
        intent = r.get('intent', 'unknown')
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print(f"\nIntent distribution:")
    for intent, count in sorted(intent_counts.items()):
        print(f"  {intent}: {count}")


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test LangGraph agent pipeline")
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to test (if not provided, runs all test queries)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output including Cypher queries"
    )

    parser.add_argument("--llm-provider", "-p", default="openai")
    parser.add_argument("--llm-model", "-m", default="gpt-4o-mini")
    # settings = get_settings()
    # settings.llm_provider = args.llm_provider
    # settings.llm_model = args.llm_model
    args = parser.parse_args()

    if args.query:
        # Test single query
        test_single_query(args.query, verbose=args.verbose)
    else:
        # Test all queries
        test_all_queries()


if __name__ == "__main__":
    main()
