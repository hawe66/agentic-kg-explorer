"""Document crawler for URL and PDF extraction."""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class Document:
    """Represents a crawled document."""

    title: str
    content: str
    source_url: Optional[str] = None
    source_path: Optional[str] = None
    doc_type: str = "article"  # paper, article, documentation
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    crawled_at: datetime = field(default_factory=datetime.now)

    @property
    def content_hash(self) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]

    @property
    def doc_id(self) -> str:
        """Generate document ID."""
        if self.source_url:
            domain = urlparse(self.source_url).netloc.replace(".", "-")
            return f"doc:{domain}:{self.content_hash}"
        elif self.source_path:
            filename = Path(self.source_path).stem
            return f"doc:{filename}:{self.content_hash}"
        return f"doc:unknown:{self.content_hash}"


class DocumentCrawler:
    """Extract text from URLs and PDFs."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AgenticKGExplorer/1.0)"
                },
            )
        return self._client

    def crawl_url(self, url: str) -> Document:
        """Fetch and extract text from URL.

        Args:
            url: Web page URL to crawl.

        Returns:
            Document with extracted content.

        Raises:
            httpx.HTTPError: If fetch fails.
            ValueError: If content extraction fails.
        """
        client = self._get_client()
        response = client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        elif soup.h1:
            title = soup.h1.get_text(strip=True)

        # Extract main content
        content = ""

        # Try common content containers
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=re.compile(r"(content|article|post|entry)", re.I))
            or soup.find(id=re.compile(r"(content|article|main)", re.I))
        )

        if main_content:
            content = main_content.get_text(separator="\n", strip=True)
        else:
            # Fallback to body
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)

        # Clean up whitespace
        content = re.sub(r"\n\s*\n", "\n\n", content)
        content = content.strip()

        if not content:
            raise ValueError(f"Could not extract content from {url}")

        # Detect document type
        doc_type = self._detect_doc_type(url, title, content)

        # Try to extract year from content or URL
        year = self._extract_year(content, url)

        return Document(
            title=title.strip() or "Untitled",
            content=content,
            source_url=url,
            doc_type=doc_type,
            year=year,
        )

    def crawl_pdf(self, file_path: str | Path) -> Document:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file.

        Returns:
            Document with extracted content.

        Raises:
            ImportError: If pymupdf not installed.
            FileNotFoundError: If file doesn't exist.
        """
        try:
            import fitz  # pymupdf
        except ImportError:
            raise ImportError("pymupdf is required for PDF extraction: pip install pymupdf")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        doc = fitz.open(file_path)

        # Extract text from all pages
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)

        content = "\n\n".join(pages)
        doc.close()

        # Extract title from first page or filename
        title = file_path.stem.replace("_", " ").replace("-", " ").title()

        # Try to detect if it's a paper (look for abstract, references)
        doc_type = "paper" if "abstract" in content.lower()[:2000] else "article"

        # Try to extract year
        year = self._extract_year(content, str(file_path))

        # Try to extract authors from first page
        authors = self._extract_authors(content[:2000]) if doc_type == "paper" else []

        return Document(
            title=title,
            content=content,
            source_path=str(file_path),
            doc_type=doc_type,
            authors=authors,
            year=year,
        )

    def crawl_text(self, text: str, title: str = "Untitled") -> Document:
        """Create document from raw text.

        Args:
            text: Raw text content.
            title: Document title.

        Returns:
            Document instance.
        """
        return Document(
            title=title,
            content=text.strip(),
            doc_type="article",
        )

    def _detect_doc_type(self, url: str, title: str, content: str) -> str:
        """Detect document type from URL and content."""
        url_lower = url.lower()

        # Check URL patterns
        if "arxiv.org" in url_lower or "papers" in url_lower:
            return "paper"
        if "github.com" in url_lower or "docs." in url_lower or "/documentation" in url_lower:
            return "documentation"

        # Check content patterns
        content_lower = content.lower()[:3000]
        if "abstract" in content_lower and "references" in content_lower:
            return "paper"

        return "article"

    def _extract_year(self, content: str, source: str) -> Optional[int]:
        """Try to extract publication year."""
        # Check source for year pattern
        year_match = re.search(r"20[12]\d", source)
        if year_match:
            return int(year_match.group())

        # Check content for copyright or date
        content_sample = content[:2000]
        year_match = re.search(r"(?:copyright|©|\d{4})\s*(20[12]\d)", content_sample, re.I)
        if year_match:
            return int(year_match.group(1))

        return None

    def _extract_authors(self, content: str) -> list[str]:
        """Try to extract author names from paper header."""
        # Simple heuristic: look for comma-separated names before abstract
        abstract_pos = content.lower().find("abstract")
        if abstract_pos == -1:
            return []

        header = content[:abstract_pos]

        # Look for author line patterns
        # Common patterns: "Name1, Name2, and Name3" or "Name1*, Name2"
        author_pattern = r"([A-Z][a-z]+ [A-Z][a-z]+(?:\s*[*†‡])?(?:\s*,\s*|\s+and\s+|$))+"
        matches = re.findall(author_pattern, header)

        if matches:
            # Clean up matches
            authors = []
            for match in matches[:5]:  # Limit to 5 authors
                name = re.sub(r"[*†‡,]", "", match).strip()
                if len(name) > 3 and " " in name:
                    authors.append(name)
            return authors

        return []

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
