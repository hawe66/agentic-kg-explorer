"""Sync all KG nodes to VDB.

Ensures every node in Neo4j has a corresponding embedding in ChromaDB.

Usage:
    poetry run python scripts/sync_kg_to_vdb.py
    poetry run python scripts/sync_kg_to_vdb.py --dry-run
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.graph.client import Neo4jClient
from src.retrieval.embedder import get_embedding_client
from src.retrieval.vector_store import get_vector_store


def build_node_text(node: dict, label: str) -> str:
    """Build unified text representation for a KG node."""
    name = node.get("name") or node.get("title") or node.get("id", "Unknown")
    description = node.get("description") or node.get("abstract") or ""

    lines = [f"[{label}] {name}"]

    if description:
        lines.append(f"Description: {description}")

    # Label-specific fields
    if label == "Method":
        if node.get("method_family"):
            lines.append(f"Family: {node['method_family']}")
        if node.get("method_type"):
            lines.append(f"Type: {node['method_type']}")
    elif label == "Implementation":
        if node.get("impl_type"):
            lines.append(f"Type: {node['impl_type']}")
        if node.get("maintainer"):
            lines.append(f"Maintainer: {node['maintainer']}")
    elif label == "Document":
        if node.get("authors"):
            authors = node["authors"] if isinstance(node["authors"], list) else [node["authors"]]
            lines.append(f"Authors: {', '.join(authors)}")
        if node.get("year"):
            lines.append(f"Year: {node['year']}")
    elif label == "Standard":
        if node.get("org"):
            lines.append(f"Organization: {node['org']}")
    elif label == "StandardVersion":
        if node.get("version"):
            lines.append(f"Version: {node['version']}")
    elif label == "Principle":
        pass  # Description is enough

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sync KG nodes to VDB")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()

    # Initialize
    settings = get_settings()
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    client.connect()

    embedder = get_embedding_client()
    if embedder is None and not args.dry_run:
        print("ERROR: No embedding provider available")
        sys.exit(1)

    store = get_vector_store()

    # Get all VDB kg_node entries
    vdb_results = store._collection.get(include=["metadatas"])
    vdb_kg_nodes = set()
    for m in vdb_results["metadatas"]:
        if m.get("source_type") == "kg_node":
            vdb_kg_nodes.add(m.get("node_id"))

    print(f"Existing VDB kg_node entries: {len(vdb_kg_nodes)}")

    # Get all KG nodes
    result = client.run_cypher("""
        MATCH (n)
        WHERE n.id IS NOT NULL
        RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS props
    """)

    kg_nodes = [(r["id"], r["label"], r["props"]) for r in result]
    print(f"Total KG nodes: {len(kg_nodes)}")

    # Find missing
    missing = [(nid, label, props) for nid, label, props in kg_nodes if nid not in vdb_kg_nodes]
    print(f"Missing from VDB: {len(missing)}")

    if not missing:
        print("All KG nodes are synced to VDB!")
        client.close()
        return

    collected_at = datetime.now(timezone.utc).isoformat()

    # Embed missing nodes
    for nid, label, props in missing:
        name = props.get("name") or props.get("title") or nid
        print(f"  Syncing: {nid} ({label})")

        if args.dry_run:
            continue

        text = build_node_text(props, label)
        embedding = embedder.embed_single(text)

        store.upsert(
            ids=[f"kg:{nid}"],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "source_type": "kg_node",
                "source_id": nid,
                "source_url": "",
                "collected_at": collected_at,
                "collector": "sync_kg_to_vdb.py",
                "node_id": nid,
                "node_label": label,
                "title": name,
                "chunk_index": 0,
                "total_chunks": 1,
            }],
        )

    client.close()

    if not args.dry_run:
        print(f"\nSynced {len(missing)} nodes to VDB")
        print(f"VDB now has {store.count} entries")


if __name__ == "__main__":
    main()
