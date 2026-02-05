"""Generate entity catalog from Neo4j for intent classification.

This script extracts all entities from the knowledge graph and saves them
to a JSON file that can be used by the intent classifier to:
1. Know what entities exist in the KG
2. Provide exact entity names to the LLM
3. Build alias mappings (CoT → m:cot)

Usage:
    poetry run python scripts/generate_entity_catalog.py
    poetry run python scripts/generate_entity_catalog.py --output data/entity_catalog.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.client import Neo4jClient


def generate_entity_catalog(output_path: Path) -> dict:
    """Extract all entities from Neo4j and build catalog."""

    catalog = {
        "principles": [],
        "methods": [],
        "implementations": [],
        "standards": [],
        "aliases": {},
        "generated_at": datetime.now().isoformat(),
    }

    with Neo4jClient() as client:
        # Principles (11 fixed)
        principles = client.run_cypher(
            "MATCH (p:Principle) RETURN p.id as id, p.name as name ORDER BY p.name"
        )
        catalog["principles"] = [
            {"id": r["id"], "name": r["name"]}
            for r in principles
        ]

        # Methods with aliases
        methods = client.run_cypher("""
            MATCH (m:Method)
            OPTIONAL MATCH (m)-[a:ADDRESSES]->(p:Principle)
            RETURN m.id as id, m.name as name, m.aliases as aliases,
                   m.method_family as family, m.maturity as maturity,
                   collect(DISTINCT p.name) as principles
            ORDER BY m.name
        """)
        for r in methods:
            catalog["methods"].append({
                "id": r["id"],
                "name": r["name"],
                "family": r["family"],
                "maturity": r["maturity"],
                "principles": r["principles"],
            })
            # Build alias map
            if r["aliases"]:
                for alias in r["aliases"]:
                    catalog["aliases"][alias.lower()] = r["id"]
            # Also add name variations
            catalog["aliases"][r["name"].lower()] = r["id"]

        # Implementations
        implementations = client.run_cypher("""
            MATCH (i:Implementation)
            OPTIONAL MATCH (i)-[impl:IMPLEMENTS]->(m:Method)
            RETURN i.id as id, i.name as name, i.aliases as aliases,
                   i.category as category,
                   collect(DISTINCT m.name) as methods
            ORDER BY i.name
        """)
        for r in implementations:
            catalog["implementations"].append({
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "methods": r["methods"],
            })
            if r["aliases"]:
                for alias in r["aliases"]:
                    catalog["aliases"][alias.lower()] = r["id"]
            catalog["aliases"][r["name"].lower()] = r["id"]

        # Standards
        standards = client.run_cypher("""
            MATCH (s:Standard)
            OPTIONAL MATCH (sv:StandardVersion)-[:HAS_VERSION]->(s)
            RETURN s.id as id, s.name as name, s.aliases as aliases,
                   collect(DISTINCT sv.version) as versions
            ORDER BY s.name
        """)
        for r in standards:
            catalog["standards"].append({
                "id": r["id"],
                "name": r["name"],
                "versions": r["versions"],
            })
            if r["aliases"]:
                for alias in r["aliases"]:
                    catalog["aliases"][alias.lower()] = r["id"]
            catalog["aliases"][r["name"].lower()] = r["id"]

    # Add common aliases manually
    common_aliases = {
        "cot": "m:cot",
        "chain of thought": "m:cot",
        "chain-of-thought": "m:cot",
        "rag": "m:rag",
        "retrieval augmented generation": "m:rag",
        "tot": "m:tot",
        "tree of thoughts": "m:tot",
        "react": "m:react",
        "otel": "std:otel",
        "opentelemetry": "std:otel",
        "a2a": "std:a2a",
        "agent to agent": "std:a2a",
        "agent-to-agent": "std:a2a",
    }
    for alias, node_id in common_aliases.items():
        if alias not in catalog["aliases"]:
            catalog["aliases"][alias] = node_id

    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Entity catalog generated: {output_path}")
    print(f"  - Principles: {len(catalog['principles'])}")
    print(f"  - Methods: {len(catalog['methods'])}")
    print(f"  - Implementations: {len(catalog['implementations'])}")
    print(f"  - Standards: {len(catalog['standards'])}")
    print(f"  - Aliases: {len(catalog['aliases'])}")

    return catalog


def main():
    parser = argparse.ArgumentParser(description="Generate entity catalog from Neo4j")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/entity_catalog.json"),
        help="Output path for catalog JSON"
    )
    args = parser.parse_args()

    generate_entity_catalog(args.output)


if __name__ == "__main__":
    main()
