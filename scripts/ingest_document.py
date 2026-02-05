"""CLI tool for ingesting documents into the Knowledge Graph.

Usage:
    poetry run python scripts/ingest_document.py --url https://example.com/article
    poetry run python scripts/ingest_document.py --pdf papers/react.pdf
    poetry run python scripts/ingest_document.py --pdf papers/react.pdf --approve-all

Options:
    --url URL       URL to crawl and ingest
    --pdf PATH      Path to PDF file to ingest
    --approve-all   Auto-approve all proposed links (skip review)
    --dry-run       Show what would be done without saving
    --embed         Also generate embeddings for ChromaDB
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.crawler import DocumentCrawler
from src.ingestion.chunker import chunk_for_embedding
from src.ingestion.linker import DocumentLinker


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into the Knowledge Graph"
    )
    parser.add_argument("--url", help="URL to crawl and ingest")
    parser.add_argument("--pdf", help="Path to PDF file to ingest")
    parser.add_argument(
        "--approve-all",
        action="store_true",
        help="Auto-approve all proposed links",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without saving",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate embeddings for ChromaDB",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence for auto-approval (default: 0.5)",
    )

    args = parser.parse_args()

    if not args.url and not args.pdf:
        parser.error("Either --url or --pdf is required")

    # Initialize components
    crawler = DocumentCrawler()
    linker = DocumentLinker()

    # Crawl document
    print("\n" + "=" * 60)
    print("STEP 1: Crawling Document")
    print("=" * 60)

    try:
        if args.url:
            print(f"Crawling URL: {args.url}")
            doc = crawler.crawl_url(args.url)
        else:
            print(f"Reading PDF: {args.pdf}")
            doc = crawler.crawl_pdf(args.pdf)

        print(f"\n  Title: {doc.title}")
        print(f"  Type: {doc.doc_type}")
        print(f"  Content length: {len(doc.content)} chars")
        print(f"  Doc ID: {doc.doc_id}")
        if doc.authors:
            print(f"  Authors: {', '.join(doc.authors)}")
        if doc.year:
            print(f"  Year: {doc.year}")

    except Exception as e:
        print(f"ERROR: Failed to crawl document: {e}")
        return 1

    # Link document to KG
    print("\n" + "=" * 60)
    print("STEP 2: Analyzing for KG Links")
    print("=" * 60)

    try:
        result = linker.link_document(doc)
        print(f"\nFound {len(result.proposed_links)} proposed links:")

        for i, link in enumerate(result.proposed_links, 1):
            conf_str = f"{link.confidence:.0%}"
            print(f"\n  {i}. [{link.entity_type}] {link.entity_name} ({link.entity_id})")
            print(f"     Relationship: {link.relationship}")
            print(f"     Confidence: {conf_str}")
            print(f"     Evidence: {link.evidence[:80]}...")

        if result.new_entities:
            print(f"\nSuggested new entities ({len(result.new_entities)}):")
            for entity in result.new_entities:
                print(f"  - [{entity.get('type', 'Unknown')}] {entity.get('name', 'Unknown')}")

    except Exception as e:
        print(f"ERROR: Failed to analyze document: {e}")
        return 1

    # Approve links
    print("\n" + "=" * 60)
    print("STEP 3: Approving Links")
    print("=" * 60)

    approved_links = []

    if args.approve_all:
        # Filter by confidence threshold
        approved_links = [
            link for link in result.proposed_links
            if link.confidence >= args.min_confidence
        ]
        print(f"\nAuto-approved {len(approved_links)} links (confidence >= {args.min_confidence:.0%})")
    else:
        # Interactive approval
        print("\nReview each proposed link (y/n/q):")
        for link in result.proposed_links:
            print(f"\n  [{link.entity_type}] {link.entity_name}")
            print(f"  Relationship: {link.relationship} (confidence: {link.confidence:.0%})")
            print(f"  Evidence: {link.evidence[:60]}...")

            while True:
                response = input("  Approve? [y/n/q]: ").strip().lower()
                if response in ("y", "yes"):
                    approved_links.append(link)
                    print("  -> Approved")
                    break
                elif response in ("n", "no"):
                    print("  -> Skipped")
                    break
                elif response in ("q", "quit"):
                    print("  -> Quit review")
                    break
                else:
                    print("  Please enter y, n, or q")

            if response in ("q", "quit"):
                break

    print(f"\n{len(approved_links)} links approved")

    # Save to Neo4j
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - Would save:")
        print("=" * 60)
        print(f"\n  Document: {doc.doc_id}")
        print(f"  Links: {len(approved_links)}")
        for link in approved_links:
            print(f"    - {link.relationship} -> {link.entity_id}")
    elif approved_links:
        print("\n" + "=" * 60)
        print("STEP 4: Saving to Neo4j")
        print("=" * 60)

        success = linker.save_document_to_kg(doc, approved_links)
        if success:
            print(f"\n  ✓ Document saved: {doc.doc_id}")
            print(f"  ✓ Created {len(approved_links)} relationships")
        else:
            print("\n  ✗ Failed to save to Neo4j")
            return 1

    # Generate embeddings
    if args.embed and not args.dry_run:
        print("\n" + "=" * 60)
        print("STEP 5: Generating Embeddings")
        print("=" * 60)

        try:
            chunks = chunk_for_embedding(doc)
            print(f"\n  Split into {len(chunks)} chunks")

            from src.retrieval.vector_store import get_vector_store

            store = get_vector_store()

            # Prepare documents for ChromaDB
            ids = []
            documents = []
            metadatas = []

            for chunk in chunks:
                chunk_id = f"doc:{doc.content_hash}:{chunk.chunk_index}"
                ids.append(chunk_id)
                documents.append(chunk.text)
                metadatas.append({
                    "source_type": "document",
                    "source_url": doc.source_url or "",
                    "node_id": doc.doc_id,
                    "node_label": "Document",
                    "title": doc.title,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                })

            # Add to ChromaDB
            store.add_documents(documents, metadatas, ids)
            print(f"  ✓ Added {len(chunks)} chunks to ChromaDB")

        except Exception as e:
            print(f"\n  ✗ Failed to generate embeddings: {e}")
            return 1

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
