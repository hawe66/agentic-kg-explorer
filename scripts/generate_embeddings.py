"""Fetch KG nodes from Neo4j, embed with OpenAI, and store in ChromaDB.

Supports incremental updates via content hashing.
ID schema: kg:{node_id} (e.g., kg:m:react)

Usage:
    poetry run python scripts/generate_embeddings.py           # Incremental (only changed nodes)
    poetry run python scripts/generate_embeddings.py --reset   # Full rebuild
    poetry run python scripts/generate_embeddings.py --dry-run # Show what would change
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.graph.client import Neo4jClient
from src.retrieval.embedder import get_embedding_client
from src.retrieval.vector_store import get_vector_store


# Hash file for incremental updates
HASH_FILE = Path(__file__).resolve().parents[1] / "data" / "embedding_hashes.json"


# ---------------------------------------------------------------------------
# Queries with relationship context
# ---------------------------------------------------------------------------

QUERY_METHODS = """
MATCH (m:Method)
OPTIONAL MATCH (m)-[addr:ADDRESSES]->(p:Principle)
OPTIONAL MATCH (impl:Implementation)-[imp:IMPLEMENTS]->(m)
WITH m,
     collect(DISTINCT {name: p.name, role: addr.role, weight: addr.weight}) AS principles,
     collect(DISTINCT {name: impl.name, level: imp.support_level}) AS implementations
RETURN m.id AS id,
       m.name AS name,
       m.description AS description,
       m.method_family AS method_family,
       m.method_type AS method_type,
       m.granularity AS granularity,
       m.year_introduced AS year_introduced,
       m.seminal_source AS seminal_source,
       principles,
       implementations
"""

QUERY_PRINCIPLES = """
MATCH (p:Principle)
OPTIONAL MATCH (m:Method)-[:ADDRESSES]->(p)
WITH p, collect(DISTINCT m.name) AS methods
RETURN p.id AS id,
       p.name AS name,
       p.description AS description,
       methods
"""

QUERY_IMPLEMENTATIONS = """
MATCH (i:Implementation)
OPTIONAL MATCH (i)-[imp:IMPLEMENTS]->(m:Method)
OPTIONAL MATCH (i)-[:COMPLIES_WITH]->(sv:StandardVersion)-[:HAS_VERSION]-(s:Standard)
WITH i,
     collect(DISTINCT {name: m.name, level: imp.support_level}) AS methods,
     collect(DISTINCT s.name) AS standards
RETURN i.id AS id,
       i.name AS name,
       i.description AS description,
       i.impl_type AS impl_type,
       i.maintainer AS maintainer,
       i.source_repo AS source_repo,
       methods,
       standards
"""

QUERY_DOCUMENTS = """
MATCH (d:Document)
OPTIONAL MATCH (d)-[:PROPOSES]->(m:Method)
WITH d, collect(DISTINCT m.name) AS proposed_methods
RETURN d.id AS id,
       d.title AS title,
       d.abstract AS abstract,
       d.doc_type AS doc_type,
       d.authors AS authors,
       d.venue AS venue,
       d.year AS year,
       proposed_methods
"""


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def build_method_text(row: dict) -> str:
    lines = [f"[Method] {row.get('name', 'Unknown')}"]
    if row.get("description"):
        lines.append(f"Description: {row['description']}")
    if row.get("method_family"):
        lines.append(f"Family: {row['method_family']}")
    if row.get("method_type"):
        lines.append(f"Type: {row['method_type']}")
    if row.get("granularity"):
        lines.append(f"Granularity: {row['granularity']}")

    principles = row.get("principles") or []
    valid_principles = [p for p in principles if p.get("name")]
    if valid_principles:
        principle_strs = []
        for p in valid_principles:
            role = p.get("role", "")
            weight = p.get("weight", "")
            suffix = f" ({role}" if role else ""
            if weight:
                suffix += f", weight: {weight}" if suffix else f" (weight: {weight}"
            if suffix:
                suffix += ")"
            principle_strs.append(f"{p['name']}{suffix}")
        lines.append(f"Addresses: {', '.join(principle_strs)}")

    implementations = row.get("implementations") or []
    valid_impls = [i for i in implementations if i.get("name")]
    if valid_impls:
        impl_strs = []
        for i in valid_impls:
            level = i.get("level", "")
            suffix = f" ({level})" if level else ""
            impl_strs.append(f"{i['name']}{suffix}")
        lines.append(f"Implemented by: {', '.join(impl_strs)}")

    if row.get("year_introduced"):
        lines.append(f"Year introduced: {row['year_introduced']}")
    if row.get("seminal_source"):
        lines.append(f"Seminal paper: {row['seminal_source']}")

    return "\n".join(lines)


def build_principle_text(row: dict) -> str:
    lines = [f"[Principle] {row.get('name', 'Unknown')}"]
    if row.get("description"):
        lines.append(f"Description: {row['description']}")
    methods = row.get("methods") or []
    valid_methods = [m for m in methods if m]
    if valid_methods:
        lines.append(f"Addressed by methods: {', '.join(valid_methods)}")
    return "\n".join(lines)


def build_implementation_text(row: dict) -> str:
    lines = [f"[Implementation] {row.get('name', 'Unknown')}"]
    if row.get("description"):
        lines.append(f"Description: {row['description']}")
    if row.get("impl_type"):
        lines.append(f"Type: {row['impl_type']}")
    if row.get("maintainer"):
        lines.append(f"Maintainer: {row['maintainer']}")

    methods = row.get("methods") or []
    valid_methods = [m for m in methods if m.get("name")]
    if valid_methods:
        method_strs = []
        for m in valid_methods:
            level = m.get("level", "")
            suffix = f" ({level})" if level else ""
            method_strs.append(f"{m['name']}{suffix}")
        lines.append(f"Implements: {', '.join(method_strs)}")

    standards = row.get("standards") or []
    valid_standards = [s for s in standards if s]
    if valid_standards:
        lines.append(f"Complies with: {', '.join(valid_standards)}")
    if row.get("source_repo"):
        lines.append(f"Repository: {row['source_repo']}")

    return "\n".join(lines)


def build_document_text(row: dict) -> str:
    lines = [f"[Document] {row.get('title', 'Unknown')}"]
    if row.get("doc_type"):
        lines.append(f"Type: {row['doc_type']}")
    if row.get("authors"):
        authors = row["authors"]
        if isinstance(authors, list):
            authors = ", ".join(authors)
        lines.append(f"Authors: {authors}")
    if row.get("venue"):
        lines.append(f"Venue: {row['venue']}")
    if row.get("year"):
        lines.append(f"Year: {row['year']}")
    if row.get("abstract"):
        lines.append(f"Abstract: {row['abstract']}")
    methods = row.get("proposed_methods") or []
    valid_methods = [m for m in methods if m]
    if valid_methods:
        lines.append(f"Proposes: {', '.join(valid_methods)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hash management for incremental updates
# ---------------------------------------------------------------------------

def load_hashes() -> dict:
    """Load stored content hashes."""
    if HASH_FILE.exists():
        with open(HASH_FILE) as f:
            return json.load(f)
    return {}


def save_hashes(hashes: dict) -> None:
    """Save content hashes."""
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HASH_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def compute_hash(text: str) -> str:
    """Compute MD5 hash of text content."""
    return hashlib.md5(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

NODE_SPECS = [
    ("Method", QUERY_METHODS, build_method_text),
    ("Principle", QUERY_PRINCIPLES, build_principle_text),
    ("Implementation", QUERY_IMPLEMENTATIONS, build_implementation_text),
    ("Document", QUERY_DOCUMENTS, build_document_text),
]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Full rebuild (clear collection and hashes)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without embedding")
    args = parser.parse_args()

    embedder = get_embedding_client()
    if embedder is None and not args.dry_run:
        print("ERROR: OPENAI_API_KEY not set. Cannot generate embeddings.")
        sys.exit(1)

    settings = get_settings()
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    client.connect()

    store = get_vector_store()

    # Load existing hashes
    if args.reset:
        old_hashes = {}
        print("Reset mode: clearing collection and hashes...")
        store.reset()
    else:
        old_hashes = load_hashes()
        print(f"Incremental mode: {len(old_hashes)} existing hashes loaded")

    collected_at = datetime.now(timezone.utc).isoformat()
    new_hashes = {}

    # Collect all nodes and determine what changed
    to_embed = []  # (entry_id, text, metadata)
    to_delete = set(old_hashes.keys())  # Start with all old, remove as we see them

    for label, query, text_builder in NODE_SPECS:
        print(f"Fetching {label} nodes with relationships...")
        rows = client.run_cypher(query)
        print(f"  Found {len(rows)} {label} nodes")

        for row in rows:
            node_id = row.get("id") or ""
            if not node_id:
                continue

            unified_text = text_builder(row)
            if not unified_text or len(unified_text) < 10:
                continue

            entry_id = f"kg:{node_id}"
            content_hash = compute_hash(unified_text)
            new_hashes[entry_id] = content_hash

            # Remove from delete set (node still exists)
            to_delete.discard(entry_id)

            # Check if changed
            if old_hashes.get(entry_id) != content_hash:
                metadata = {
                    "source_type": "kg_node",
                    "source_id": node_id,
                    "source_url": "",
                    "collected_at": collected_at,
                    "collector": "generate_embeddings.py",
                    "node_id": node_id,
                    "node_label": label,
                    "title": row.get("name") or row.get("title") or node_id,
                    "chunk_index": 0,
                    "total_chunks": 1,
                }
                to_embed.append((entry_id, unified_text, metadata))

    client.close()

    # Report changes
    print(f"\n--- Changes ---")
    print(f"  New/Updated: {len(to_embed)}")
    print(f"  Deleted: {len(to_delete)}")
    print(f"  Unchanged: {len(new_hashes) - len(to_embed)}")

    if args.dry_run:
        print("\n[Dry run] Would embed:")
        for entry_id, _, _ in to_embed[:10]:
            print(f"  {entry_id}")
        if len(to_embed) > 10:
            print(f"  ... and {len(to_embed) - 10} more")
        print("\n[Dry run] Would delete:")
        for entry_id in list(to_delete)[:10]:
            print(f"  {entry_id}")
        return

    # Delete removed nodes
    if to_delete:
        print(f"\nDeleting {len(to_delete)} removed entries...")
        store._collection.delete(ids=list(to_delete))

    # Embed and upsert changed nodes
    if to_embed:
        print(f"\nEmbedding {len(to_embed)} new/updated nodes...")
        ids = [e[0] for e in to_embed]
        texts = [e[1] for e in to_embed]
        metadatas = [e[2] for e in to_embed]

        batch_size = 512
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            print(f"  Batch {i // batch_size + 1}: {len(batch)} texts")
            all_embeddings.extend(embedder.embed_texts(batch))

        store.upsert(
            ids=ids,
            documents=texts,
            embeddings=all_embeddings,
            metadatas=metadatas,
        )

    # Save new hashes
    save_hashes(new_hashes)

    print(f"\nDone! ChromaDB collection has {store.count} entries.")
    print(f"Hash file: {HASH_FILE}")


if __name__ == "__main__":
    main()
