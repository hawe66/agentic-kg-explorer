"""Fetch KG nodes from Neo4j, embed with OpenAI, and store in ChromaDB.

Usage:
    poetry run python scripts/generate_embeddings.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.graph.client import Neo4jClient
from src.retrieval.embedder import get_embedding_client
from src.retrieval.vector_store import get_vector_store


# ---------------------------------------------------------------------------
# Node-fetching queries
# ---------------------------------------------------------------------------

QUERIES = {
    "Method": {
        "query": "MATCH (m:Method) RETURN m.id AS id, m.name AS name, m.description AS description",
        "fields": ["name", "description"],
    },
    "Principle": {
        "query": "MATCH (p:Principle) RETURN p.id AS id, p.name AS name, p.description AS description",
        "fields": ["description"],
    },
    "Document": {
        "query": "MATCH (d:Document) RETURN d.id AS id, d.title AS title, d.abstract AS abstract",
        "fields": ["title", "abstract"],
    },
    "Implementation": {
        "query": "MATCH (i:Implementation) RETURN i.id AS id, i.name AS name, i.description AS description",
        "fields": ["name", "description"],
    },
}


def main() -> None:
    embedder = get_embedding_client()
    if embedder is None:
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

    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metadatas: list[dict] = []

    for label, spec in QUERIES.items():
        print(f"Fetching {label} nodes...")
        rows = client.run_cypher(spec["query"])
        print(f"  Found {len(rows)} {label} nodes")

        for row in rows:
            node_id = row.get("id") or ""
            for field in spec["fields"]:
                text = row.get(field)
                if not text:
                    continue
                entry_id = f"{node_id}:{field}"
                all_ids.append(entry_id)
                all_texts.append(text)
                all_metadatas.append({
                    "node_id": node_id,
                    "node_label": label,
                    "field": field,
                })

    client.close()

    if not all_texts:
        print("No texts to embed. Check your Neo4j data.")
        sys.exit(1)

    print(f"\nEmbedding {len(all_texts)} texts...")

    # Batch embed (OpenAI supports up to 2048 inputs per call)
    batch_size = 512
    all_embeddings: list[list[float]] = []
    for i in range(0, len(all_texts), batch_size):
        batch = all_texts[i : i + batch_size]
        print(f"  Batch {i // batch_size + 1}: {len(batch)} texts")
        all_embeddings.extend(embedder.embed_texts(batch))

    print(f"Upserting {len(all_ids)} entries into ChromaDB...")
    store.upsert(
        ids=all_ids,
        documents=all_texts,
        embeddings=all_embeddings,
        metadatas=all_metadatas,
    )

    print(f"Done! ChromaDB collection has {store.count} entries.")


if __name__ == "__main__":
    main()
