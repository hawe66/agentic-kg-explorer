"""Run a Cypher migration file against the live Neo4j database.

Usage:
    poetry run python scripts/run_migration.py neo4j/migrations/001_add_impl_descriptions.cypher
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.graph.client import Neo4jClient


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_migration.py <cypher_file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    settings = get_settings()
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    client.connect()

    count = client.run_cypher_file(filepath)
    print(f"Executed {count} statements from {filepath.name}")

    client.close()


if __name__ == "__main__":
    main()
