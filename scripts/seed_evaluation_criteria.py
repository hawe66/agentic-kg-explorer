"""Seed EvaluationCriteria nodes to Neo4j.

Usage:
    poetry run python scripts/seed_evaluation_criteria.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.graph.client import Neo4jClient


def main():
    """Load seed_evaluation.cypher into Neo4j."""
    settings = get_settings()

    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    client.connect()

    # Run the seed file
    seed_file = Path(__file__).resolve().parents[1] / "neo4j" / "seed_evaluation.cypher"
    print(f"Loading seed data from: {seed_file}")

    count = client.run_cypher_file(seed_file)
    print(f"Executed {count} statements")

    # Verify
    result = client.run_cypher("""
        MATCH (ec:EvaluationCriteria)-[:DERIVED_FROM]->(p:Principle)
        RETURN ec.agent_target AS agent, count(ec) AS count, collect(ec.name) AS criteria
        ORDER BY ec.agent_target
    """)

    print("\nEvaluationCriteria by agent:")
    for row in result:
        print(f"  {row['agent']}: {row['count']} criteria")
        for name in row['criteria']:
            print(f"    - {name}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
