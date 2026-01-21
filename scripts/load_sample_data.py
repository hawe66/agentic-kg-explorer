#!/usr/bin/env python3
"""Script to load sample data into Neo4j."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import Neo4jClient
from data.sample_data import get_all_sample_data


def load_sample_data(clear_first: bool = False) -> None:
    """Load all sample data into Neo4j.
    
    Args:
        clear_first: If True, clear the database before loading
    """
    client = Neo4jClient()
    
    try:
        client.connect()
        
        if clear_first:
            print("⚠️  Clearing database...")
            client.clear_database()
        
        # Setup schema
        print("📐 Setting up schema constraints...")
        client.setup_constraints()
        
        # Get sample data
        data = get_all_sample_data()
        
        # Load sources
        print(f"\n📚 Loading {len(data['sources'])} sources...")
        for source in data["sources"]:
            client.create_source(source)
            print(f"  ✓ {source.name}")
        
        # Load authors
        print(f"\n👤 Loading {len(data['authors'])} authors...")
        for author in data["authors"]:
            client.create_author(author)
            print(f"  ✓ {author.name}")
        
        # Load concepts
        print(f"\n💡 Loading {len(data['concepts'])} concepts...")
        for concept in data["concepts"]:
            client.create_concept(concept)
            print(f"  ✓ {concept.name} [{concept.category_sub.value}]")
        
        # Load documents
        print(f"\n📄 Loading {len(data['documents'])} documents...")
        for doc in data["documents"]:
            client.create_document(doc)
            print(f"  ✓ {doc.title[:50]}...")
        
        # Load relationships
        print(f"\n🔗 Loading {len(data['relationships'])} relationships...")
        for rel in data["relationships"]:
            try:
                client.create_relationship(rel)
                print(f"  ✓ {rel.source_id} -[{rel.rel_type.value}]-> {rel.target_id}")
            except Exception as e:
                print(f"  ✗ Failed: {rel.source_id} -> {rel.target_id}: {e}")
        
        # Print stats
        print("\n" + "=" * 50)
        stats = client.get_stats()
        print("📊 Database Statistics:")
        print(f"  Total nodes: {stats['total_nodes']}")
        print(f"  Total relationships: {stats['total_relationships']}")
        print("  Nodes by label:")
        for label, count in stats['nodes_by_label'].items():
            print(f"    - {label}: {count}")
        
        print("\n✅ Sample data loaded successfully!")
        
    finally:
        client.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Load sample data into Neo4j")
    parser.add_argument(
        "--clear", 
        action="store_true", 
        help="Clear database before loading"
    )
    args = parser.parse_args()
    
    load_sample_data(clear_first=args.clear)


if __name__ == "__main__":
    main()
