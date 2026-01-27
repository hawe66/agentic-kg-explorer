"""
Agentic AI Knowledge Graph - Sample Data

NOTE: Seed data is now maintained in Cypher format at:
  - neo4j/seed_data.cypher

To load seed data, use:
  from src.graph import Neo4jClient

  client = Neo4jClient()
  client.initialize(clear_first=True)

Or run from command line:
  python scripts/load_sample_data.py --clear
"""

# This file is kept for backwards compatibility.
# All actual data definitions are in neo4j/seed_data.cypher

SEED_DATA_PATH = "neo4j/seed_data.cypher"
SCHEMA_PATH = "neo4j/schema.cypher"
