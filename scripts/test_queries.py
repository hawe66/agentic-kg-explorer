#!/usr/bin/env python3
"""
Agentic AI Knowledge Graph - Query Test Script

Tests the knowledge graph with validation and domain-specific queries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Neo4jClient


def test_queries():
    """Run test queries to verify the knowledge graph."""
    print("=" * 60)
    print("Agentic AI Knowledge Graph - Query Tests")
    print("=" * 60)

    with Neo4jClient() as client:
        # Test 1: Basic statistics
        print("\n[Test 1] Database Statistics")
        stats = client.get_stats()
        print(f"  Total Nodes: {stats.total_nodes}")
        print(f"  Total Relationships: {stats.total_relationships}")
        print("  Nodes by Label:")
        for label, count in sorted(stats.nodes_by_label.items()):
            print(f"    {label}: {count}")

        # Test 2: Principles coverage
        print("\n[Test 2] Principles Coverage (Methods + Implementations)")
        coverage = client.get_principles_coverage()
        for row in coverage:
            print(f"  {row['principle']}: {row['method_count']} methods, {row['impl_count']} implementations")

        # Test 3: Principle -> Method -> Implementation paths
        print("\n[Test 3] Principle -> Method -> Implementation Paths (sample)")
        paths = client.get_principle_method_impl_paths()
        for i, path in enumerate(paths[:5]):  # Show first 5
            impls = ", ".join(path["implementations"][:3])
            if len(path["implementations"]) > 3:
                impls += f" (+{len(path['implementations']) - 3} more)"
            print(f"  {path['principle']} <- {path['method']} <- [{impls}]")
        if len(paths) > 5:
            print(f"  ... and {len(paths) - 5} more paths")

        # Test 4: Method family distribution
        print("\n[Test 4] Method Family Distribution")
        families = client.get_method_family_distribution()
        for row in families:
            print(f"  {row['family']}: {row['count']}")

        # Test 5: Standard compliance
        print("\n[Test 5] Standard Compliance Status")
        compliance = client.get_standard_compliance()
        if compliance:
            for row in compliance:
                print(f"  {row['implementation']} -> {row['standard']} v{row['version']} ({row['role']}/{row['level']})")
        else:
            print("  No compliance relationships found")

        # Test 6: Methods for a specific principle
        print("\n[Test 6] Methods Addressing 'Reasoning' Principle")
        methods = client.get_methods_by_principle("p:reasoning")
        for m in methods[:5]:
            print(f"  {m['name']} ({m['family']}) - role: {m['role']}, weight: {m['weight']}")
        if len(methods) > 5:
            print(f"  ... and {len(methods) - 5} more")

        # Test 7: Implementations of ReAct
        print("\n[Test 7] Implementations of ReAct Method")
        impls = client.get_implementations_by_method("m:react")
        for impl in impls:
            print(f"  {impl['name']} ({impl['impl_type']}) - support: {impl['support_level']}")

        # Test 8: Composite methods
        print("\n[Test 8] Composite Methods and Their Components")
        composites = client.get_composite_methods()
        for c in composites:
            print(f"  {c['composite_method']} = {' + '.join(c['components'])}")

        # Test 9: Search methods
        print("\n[Test 9] Search Methods Containing 'RAG'")
        results = client.search_methods("RAG", limit=5)
        for r in results:
            print(f"  {r['name']} ({r['family']})")

        # Test 10: Validation - Orphan checks
        print("\n[Test 10] Data Quality Validation")

        orphan_methods = client.get_orphan_methods()
        print(f"  Methods without ADDRESSES -> Principle: {len(orphan_methods)}")
        for m in orphan_methods[:3]:
            print(f"    - {m['name']}")

        orphan_impls = client.get_orphan_implementations()
        print(f"  Implementations without IMPLEMENTS -> Method: {len(orphan_impls)}")
        for i in orphan_impls[:3]:
            print(f"    - {i['name']}")

        no_paper = client.get_methods_without_paper()
        print(f"  Methods without paper/seminal_source: {len(no_paper)}")

        uncovered = client.get_uncovered_principles()
        print(f"  Principles with no methods: {len(uncovered)}")
        for p in uncovered:
            print(f"    - {p['name']}")

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)


if __name__ == "__main__":
    test_queries()
