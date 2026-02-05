"""Document chunking strategies for embedding."""

import re
from dataclasses import dataclass
from typing import Iterator

from .crawler import Document


@dataclass
class Chunk:
    """A chunk of document text for embedding."""

    text: str
    chunk_index: int
    total_chunks: int
    doc_id: str
    doc_title: str
    source_url: str | None = None
    source_path: str | None = None
    start_char: int = 0
    end_char: int = 0

    @property
    def chunk_id(self) -> str:
        """Generate chunk ID."""
        return f"{self.doc_id}:chunk:{self.chunk_index}"


class DocumentChunker:
    """Split documents into chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters.
            chunk_overlap: Overlap between consecutive chunks.
            min_chunk_size: Minimum chunk size (smaller chunks are merged).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, doc: Document) -> list[Chunk]:
        """Split document into chunks.

        Args:
            doc: Document to chunk.

        Returns:
            List of Chunk objects.
        """
        chunks = list(self._generate_chunks(doc))

        # Update total_chunks for all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _generate_chunks(self, doc: Document) -> Iterator[Chunk]:
        """Generate chunks from document content."""
        content = doc.content
        if not content:
            return

        # Split by paragraphs first
        paragraphs = self._split_paragraphs(content)

        current_chunk = []
        current_size = 0
        chunk_index = 0
        start_char = 0

        for para in paragraphs:
            para_len = len(para)

            # If paragraph itself is too large, split it
            if para_len > self.chunk_size:
                # Flush current chunk first
                if current_chunk:
                    text = "\n\n".join(current_chunk)
                    yield Chunk(
                        text=text,
                        chunk_index=chunk_index,
                        total_chunks=0,  # Will be updated later
                        doc_id=doc.doc_id,
                        doc_title=doc.title,
                        source_url=doc.source_url,
                        source_path=doc.source_path,
                        start_char=start_char,
                        end_char=start_char + len(text),
                    )
                    chunk_index += 1
                    start_char += len(text) + 2  # +2 for paragraph separator
                    current_chunk = []
                    current_size = 0

                # Split large paragraph by sentences
                for sentence_chunk in self._split_large_text(para):
                    yield Chunk(
                        text=sentence_chunk,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        doc_id=doc.doc_id,
                        doc_title=doc.title,
                        source_url=doc.source_url,
                        source_path=doc.source_path,
                        start_char=start_char,
                        end_char=start_char + len(sentence_chunk),
                    )
                    chunk_index += 1
                    start_char += len(sentence_chunk) + 2
                continue

            # Check if adding this paragraph exceeds chunk size
            if current_size + para_len + 2 > self.chunk_size and current_chunk:
                # Flush current chunk
                text = "\n\n".join(current_chunk)
                yield Chunk(
                    text=text,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    doc_id=doc.doc_id,
                    doc_title=doc.title,
                    source_url=doc.source_url,
                    source_path=doc.source_path,
                    start_char=start_char,
                    end_char=start_char + len(text),
                )
                chunk_index += 1
                start_char += len(text) + 2

                # Start new chunk with overlap (include last paragraph if fits)
                if self.chunk_overlap > 0 and current_chunk:
                    last_para = current_chunk[-1]
                    if len(last_para) <= self.chunk_overlap:
                        current_chunk = [last_para]
                        current_size = len(last_para)
                    else:
                        current_chunk = []
                        current_size = 0
                else:
                    current_chunk = []
                    current_size = 0

            # Add paragraph to current chunk
            current_chunk.append(para)
            current_size += para_len + 2

        # Flush remaining content
        if current_chunk:
            text = "\n\n".join(current_chunk)
            if len(text) >= self.min_chunk_size or chunk_index == 0:
                yield Chunk(
                    text=text,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    doc_id=doc.doc_id,
                    doc_title=doc.title,
                    source_url=doc.source_url,
                    source_path=doc.source_path,
                    start_char=start_char,
                    end_char=start_char + len(text),
                )

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines or single newlines followed by indentation
        paragraphs = re.split(r"\n\s*\n+", text)
        # Filter empty paragraphs and strip whitespace
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_large_text(self, text: str) -> Iterator[str]:
        """Split large text by sentences, keeping chunks under limit."""
        # Split by sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If single sentence is too large, split by words
            if sentence_len > self.chunk_size:
                if current_chunk:
                    yield " ".join(current_chunk)
                    current_chunk = []
                    current_size = 0

                # Split by words
                words = sentence.split()
                word_chunk = []
                word_size = 0

                for word in words:
                    if word_size + len(word) + 1 > self.chunk_size and word_chunk:
                        yield " ".join(word_chunk)
                        word_chunk = []
                        word_size = 0
                    word_chunk.append(word)
                    word_size += len(word) + 1

                if word_chunk:
                    yield " ".join(word_chunk)
                continue

            # Check if adding this sentence exceeds limit
            if current_size + sentence_len + 1 > self.chunk_size and current_chunk:
                yield " ".join(current_chunk)
                current_chunk = []
                current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_len + 1

        if current_chunk:
            yield " ".join(current_chunk)


def chunk_for_embedding(
    doc: Document,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Chunk]:
    """Convenience function to chunk a document.

    Args:
        doc: Document to chunk.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.

    Returns:
        List of chunks.
    """
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_document(doc)
