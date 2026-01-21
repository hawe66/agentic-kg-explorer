#!/usr/bin/env python3
"""Script to test basic Cypher queries against the Knowledge Graph."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Neo4jClient, MidCategory, SubCategory


def test_queries():
    """Run test queries to verify the knowledge graph."""
    client = Neo4jClient()
    
    try:
        client.connect()
        
        print("=" * 60)
        print("🧪 Testing Knowledge Graph Queries")
        print("=" * 60)
        
        # Test 1: Basic stats
        print("\n📊 Test 1: Database Statistics")
        stats = client.get_stats()
        print(f"  Nodes: {stats['total_nodes']}")
        print(f"  Relationships: {stats['total_relationships']}")
        
        # Test 2: Search documents by keyword
        print("\n🔍 Test 2: Search documents containing 'Reflexion'")
        results = client.search_documents("Reflexion")
        for r in results:
            print(f"  - {r['title'][:50]}...")
        
        # Test 3: Get concepts by category
        print("\n📂 Test 3: Concepts in 'Self-Reflection' category")
        concepts = client.find_concepts_by_category(
            sub_category=SubCategory.SELF_REFLECTION
        )
        for c in concepts:
            print(f"  - {c.name}: {c.definition[:50] if c.definition else 'No definition'}...")
        
        # Test 4: Get document with related concepts
        print("\n📄 Test 4: Document 'doc-reflexion' with concepts")
        doc_data = client.get_document_with_concepts("doc-reflexion")
        if doc_data:
            print(f"  Document: {doc_data['document']['title']}")
            print("  Related concepts:")
            for item in doc_data['concepts']:
                if item['concept']:
                    print(f"    - [{item['relation']}] {item['concept']['name']}")
        
        # Test 5: Get related concepts (graph traversal)
        print("\n🕸️  Test 5: Concepts related to 'Chain-of-Thought' (depth=2)")
        related = client.get_related_concepts("concept-cot", depth=2)
        for r in related:
            print(f"  - {r['name']} (distance: {r['distance']})")
        
        # Test 6: Custom Cypher - Find papers that cite CoT
        print("\n📑 Test 6: Documents that cite Chain-of-Thought paper")
        query = """
        MATCH (d:Document)-[:CITES]->(cited:Document {id: 'doc-cot'})
        RETURN d.title AS title
        """
        results = client.run_cypher(query)
        for r in results:
            print(f"  - {r['title']}")
        
        # Test 7: Custom Cypher - Path between concepts
        print("\n🛤️  Test 7: Path from LangGraph to Chain-of-Thought")
        query = """
        MATCH path = shortestPath(
            (a:Concept {id: 'concept-langgraph'})-[*]-(b:Concept {id: 'concept-cot'})
        )
        RETURN [node in nodes(path) | 
            CASE WHEN node:Concept THEN node.name ELSE node.title END
        ] AS path_nodes
        """
        results = client.run_cypher(query)
        for r in results:
            print(f"  Path: {' -> '.join(r['path_nodes'])}")
        
        # Test 8: Custom Cypher - Competing tools
        print("\n⚔️  Test 8: Competing tools/frameworks")
        query = """
        MATCH (a:Concept)-[:COMPETES_WITH]->(b:Concept)
        RETURN a.name AS tool_a, b.name AS tool_b
        """
        results = client.run_cypher(query)
        for r in results:
            print(f"  - {r['tool_a']} vs {r['tool_b']}")
        
        # Test 9: Category distribution
        print("\n📊 Test 9: Concepts by Mid-Category")
        query = """
        MATCH (c:Concept)
        RETURN c.category_mid AS category, count(c) AS count
        ORDER BY count DESC
        """
        results = client.run_cypher(query)
        for r in results:
            print(f"  - {r['category']}: {r['count']}")
        
        # Test 10: Most connected concepts
        print("\n🌟 Test 10: Most connected concepts (by relationship count)")
        query = """
        MATCH (c:Concept)-[r]-()
        RETURN c.name AS concept, count(r) AS connections
        ORDER BY connections DESC
        LIMIT 5
        """
        results = client.run_cypher(query)
        for r in results:
            print(f"  - {r['concept']}: {r['connections']} connections")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    finally:
        client.close()


if __name__ == "__main__":
    test_queries()
