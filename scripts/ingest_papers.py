"""Ingest documents from data/papers/ into Neo4j and ChromaDB.

Supports: PDF (.pdf), Markdown (.md)

Reads manifest.yaml for document metadata, parses files, chunks text,
creates Neo4j nodes, and embeds chunks to ChromaDB.

Usage:
    poetry run python scripts/ingest_papers.py           # Ingest all documents
    poetry run python scripts/ingest_papers.py --dry-run # Preview without changes
    poetry run python scripts/ingest_papers.py --reset   # Re-ingest all (clear existing)
"""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.graph.client import Neo4jClient
from src.retrieval.embedder import get_embedding_client
from src.retrieval.vector_store import get_vector_store


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAPERS_DIR = Path(__file__).resolve().parents[1] / "data" / "papers"
MANIFEST_FILE = PAPERS_DIR / "manifest.yaml"

# Chunking parameters
CHUNK_SIZE = 500  # tokens (approximate via chars / 4)
CHUNK_OVERLAP = 100


# ---------------------------------------------------------------------------
# File Parsing (PDF, Markdown)
# ---------------------------------------------------------------------------

def parse_file(file_path: Path) -> str:
    """Extract text from file based on extension."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)
    elif suffix in (".md", ".markdown"):
        return parse_markdown(file_path)
    elif suffix == ".txt":
        return file_path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def parse_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: poetry add pymupdf")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def parse_markdown(md_path: Path) -> str:
    """Extract text from Markdown file.

    Keeps the markdown structure for better chunking.
    """
    return md_path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks.

    Uses character-based approximation (4 chars ≈ 1 token).
    """
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + char_chunk_size

        # Try to break at paragraph or sentence boundary
        if end < text_len:
            # Look for paragraph break
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + char_chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in [". ", ".\n", "? ", "!\n"]:
                    sent_break = text.rfind(sep, start, end)
                    if sent_break > start + char_chunk_size // 2:
                        end = sent_break + len(sep)
                        break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - char_overlap

    return chunks


# ---------------------------------------------------------------------------
# Neo4j Operations
# ---------------------------------------------------------------------------

def create_document_node(client: Neo4jClient, paper: dict) -> None:
    """Create or update Document node in Neo4j."""
    query = """
    MERGE (d:Document {id: $id})
    SET d.title = $title,
        d.authors = $authors,
        d.year = $year,
        d.venue = $venue,
        d.doc_type = $doc_type,
        d.abstract = $abstract
    """
    params = {
        "id": paper["doc_id"],
        "title": paper.get("title", ""),
        "authors": paper.get("authors", []),
        "year": paper.get("year"),
        "venue": paper.get("venue", ""),
        "doc_type": paper.get("doc_type", "paper"),
        "abstract": paper.get("abstract", ""),
    }
    client.run_cypher(query, params)


def create_method_node(client: Neo4jClient, method: dict, doc_id: str) -> None:
    """Create Method node and relationships."""
    # Create Method
    query = """
    MERGE (m:Method {id: $id})
    SET m.name = $name,
        m.description = $description,
        m.method_family = $method_family,
        m.method_type = $method_type,
        m.granularity = $granularity
    """
    params = {
        "id": method["id"],
        "name": method.get("name", ""),
        "description": method.get("description", ""),
        "method_family": method.get("method_family", ""),
        "method_type": method.get("method_type", ""),
        "granularity": method.get("granularity", "atomic"),
    }
    client.run_cypher(query, params)

    # Create PROPOSES relationship
    query = """
    MATCH (d:Document {id: $doc_id})
    MATCH (m:Method {id: $method_id})
    MERGE (d)-[:PROPOSES]->(m)
    """
    client.run_cypher(query, {"doc_id": doc_id, "method_id": method["id"]})

    # Create ADDRESSES relationships
    for addr in method.get("addresses", []):
        query = """
        MATCH (m:Method {id: $method_id})
        MATCH (p:Principle {id: $principle_id})
        MERGE (m)-[r:ADDRESSES]->(p)
        SET r.role = $role, r.weight = $weight
        """
        client.run_cypher(query, {
            "method_id": method["id"],
            "principle_id": addr["principle"],
            "role": addr.get("role", "primary"),
            "weight": addr.get("weight", 1.0),
        })


# ---------------------------------------------------------------------------
# VDB Operations
# ---------------------------------------------------------------------------

def embed_method_node(
    store,
    embedder,
    method: dict,
    doc_id: str,
    collected_at: str,
) -> None:
    """Embed a Method node summary to VDB."""
    method_id = method["id"]
    name = method.get("name", method_id)
    description = method.get("description", "")
    method_family = method.get("method_family", "")

    # Build unified text
    lines = [f"[Method] {name}"]
    if description:
        lines.append(f"Description: {description}")
    if method_family:
        lines.append(f"Family: {method_family}")
    if method.get("addresses"):
        principles = [a["principle"] for a in method["addresses"]]
        lines.append(f"Addresses: {', '.join(principles)}")

    text = "\n".join(lines)
    embedding = embedder.embed_single(text)

    store.upsert(
        ids=[f"kg:{method_id}"],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{
            "source_type": "kg_node",
            "source_id": method_id,
            "source_url": "",
            "collected_at": collected_at,
            "collector": "ingest_papers.py",
            "node_id": method_id,
            "node_label": "Method",
            "title": name,
            "chunk_index": 0,
            "total_chunks": 1,
        }],
    )


def embed_and_store_chunks(
    store,
    embedder,
    chunks: list[str],
    paper: dict,
    collected_at: str,
) -> int:
    """Embed chunks and store in ChromaDB.

    Returns number of chunks stored.
    """
    doc_id = paper["doc_id"]
    title = paper.get("title", doc_id)

    ids = []
    texts = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        # ID: doc:{doc_id}:{chunk_index}
        entry_id = f"{doc_id}:{i}"

        # Build text with context
        text = f"[Document] {title}\n\n{chunk}"

        metadata = {
            "source_type": "paper",
            "source_id": doc_id,
            "source_url": "",  # Could add arxiv URL if available
            "collected_at": collected_at,
            "collector": "ingest_papers.py",
            "node_id": doc_id,
            "node_label": "Document",
            "title": title,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }

        ids.append(entry_id)
        texts.append(text)
        metadatas.append(metadata)

    if not texts:
        return 0

    # Batch embed
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        all_embeddings.extend(embedder.embed_texts(batch))

    # Store
    store.upsert(
        ids=ids,
        documents=texts,
        embeddings=all_embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    """Load papers from manifest.yaml."""
    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_FILE}")
        sys.exit(1)

    with open(MANIFEST_FILE) as f:
        data = yaml.safe_load(f)

    return data.get("papers", []) or []


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest papers into KG and VDB")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--reset", action="store_true", help="Re-ingest all papers")
    args = parser.parse_args()

    papers = load_manifest()
    if not papers:
        print("No papers in manifest. Add entries to data/papers/manifest.yaml")
        return

    print(f"Found {len(papers)} papers in manifest")

    # Initialize clients
    embedder = get_embedding_client()
    if embedder is None and not args.dry_run:
        print("ERROR: No embedding provider available")
        sys.exit(1)

    settings = get_settings()
    neo4j_client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    neo4j_client.connect()

    store = get_vector_store()
    collected_at = datetime.now(timezone.utc).isoformat()

    # Process each paper
    total_chunks = 0
    for paper in papers:
        file_name = paper.get("file", "")
        doc_id = paper.get("doc_id", "")
        title = paper.get("title", file_name)

        if not doc_id:
            print(f"SKIP: {file_name} - missing doc_id")
            continue

        file_path = PAPERS_DIR / file_name
        if not file_path.exists():
            print(f"SKIP: {file_name} - file not found")
            continue

        print(f"\nProcessing: {title}")

        if args.dry_run:
            print(f"  [Dry run] Would parse: {file_path}")
            print(f"  [Dry run] Would create Document node: {doc_id}")
            for method in paper.get("proposes", []):
                print(f"  [Dry run] Would create Method node: {method['id']}")
            continue

        # Parse file
        print(f"  Parsing {file_path.suffix} file...")
        text = parse_file(file_path)
        print(f"  Extracted {len(text)} characters")

        # Chunk
        chunks = chunk_text(text)
        print(f"  Created {len(chunks)} chunks")

        # Reset existing chunks if requested
        if args.reset:
            prefix = f"{doc_id}:"
            store.delete_by_prefix(prefix)
            print(f"  Deleted existing chunks with prefix: {prefix}")

        # Create Neo4j nodes
        print(f"  Creating Document node...")
        create_document_node(neo4j_client, paper)

        for method in paper.get("proposes", []):
            print(f"  Creating Method node: {method['id']}")
            create_method_node(neo4j_client, method, doc_id)
            embed_method_node(store, embedder, method, doc_id, collected_at)
            print(f"  Embedded Method: {method['id']}")

        # Embed and store
        print(f"  Embedding and storing chunks...")
        n_stored = embed_and_store_chunks(store, embedder, chunks, paper, collected_at)
        total_chunks += n_stored
        print(f"  Stored {n_stored} chunks")

    neo4j_client.close()

    if not args.dry_run:
        print(f"\nDone! Ingested {len(papers)} papers, {total_chunks} total chunks")
        print(f"ChromaDB now has {store.count} entries")


if __name__ == "__main__":
    main()
