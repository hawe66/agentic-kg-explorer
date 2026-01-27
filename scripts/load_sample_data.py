#!/usr/bin/env python3
"""
Agentic AI Knowledge Graph - Database Initialization Script

Loads schema and seed data from Cypher files into Neo4j.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Neo4jClient


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Agentic AI Knowledge Graph database"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear database before loading"
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Only setup schema (no seed data)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics only"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Agentic AI Knowledge Graph - Database Setup")
    print("=" * 60)

    with Neo4jClient() as client:
        # Stats only mode
        if args.stats:
            print("\n[Statistics Mode]")
            stats = client.get_stats()
            print_stats(stats)
            return

        # Schema only mode
        if args.schema_only:
            print("\n[Schema Only Mode]")
            if args.clear:
                print("Clearing database...")
                client.clear_database()
            print("Setting up schema...")
            count = client.setup_schema()
            print(f"Executed {count} schema statements")
            print("\nSchema setup complete!")
            return

        # Full initialization
        print("\n[Full Initialization Mode]")
        if args.clear:
            print("Clearing database...")
            client.clear_database()

        print("Setting up schema (constraints & indexes)...")
        schema_count = client.setup_schema()
        print(f"  Executed {schema_count} schema statements")

        print("\nLoading seed data...")
        seed_count = client.load_seed_data()
        print(f"  Executed {seed_count} seed data statements")

        print("\n" + "-" * 60)
        stats = client.get_stats()
        print_stats(stats)

        print("\nDatabase initialized successfully!")


def print_stats(stats):
    """Print database statistics in a formatted way."""
    print(f"\nTotal Nodes: {stats.total_nodes}")
    print(f"Total Relationships: {stats.total_relationships}")

    print("\nNodes by Label:")
    for label, count in sorted(stats.nodes_by_label.items()):
        print(f"  {label}: {count}")

    print("\nRelationships by Type:")
    for rel_type, count in sorted(stats.relationships_by_type.items()):
        print(f"  {rel_type}: {count}")


if __name__ == "__main__":
    main()
