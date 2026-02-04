"""Document to Knowledge Graph linker using LLM extraction."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import get_settings
from src.agents.providers.router import get_provider
from src.graph.client import Neo4jClient

from .crawler import Document


@dataclass
class ProposedLink:
    """A proposed relationship between a Document and a KG entity."""

    entity_id: str
    entity_name: str
    entity_type: str  # Method, Implementation, Standard
    relationship: str  # PROPOSES, EVALUATES, DESCRIBES, USES
    evidence: str  # Quote or reason for the link
    confidence: float  # 0.0-1.0


@dataclass
class LinkingResult:
    """Result of linking a document to the KG."""

    doc_id: str
    proposed_links: list[ProposedLink]
    new_entities: list[dict]  # Entities not in KG that could be added


class DocumentLinker:
    """Extract relationships between Documents and KG entities."""

    def __init__(self):
        self._entity_catalog: Optional[dict] = None

    def link_document(
        self,
        doc: Document,
        max_content_length: int = 4000,
    ) -> LinkingResult:
        """Use LLM to identify Methods/Implementations mentioned in document.

        Args:
            doc: Document to analyze.
            max_content_length: Max content length to send to LLM.

        Returns:
            LinkingResult with proposed links.
        """
        catalog = self._load_entity_catalog()
        provider = get_provider()

        if provider is None:
            print("[DocumentLinker] No LLM provider available, using heuristic linking")
            return self._heuristic_link(doc, catalog)

        # Prepare content sample
        content_sample = doc.content[:max_content_length]
        if len(doc.content) > max_content_length:
            content_sample += "\n[...truncated...]"

        # Build prompt
        methods_list = ", ".join(
            f"{m['name']} ({m['id']})" for m in catalog.get("methods", [])[:30]
        )
        impls_list = ", ".join(
            f"{i['name']} ({i['id']})" for i in catalog.get("implementations", [])[:20]
        )

        prompt = f"""Analyze this document and identify which Agentic AI concepts it discusses.

Document Title: {doc.title}
Document Type: {doc.doc_type}

Content:
{content_sample}

---

Known entities in our Knowledge Graph:

Methods: {methods_list}

Implementations: {impls_list}

---

For each entity mentioned or discussed, specify:
1. entity_id: The ID from the list above (e.g., "m:react")
2. relationship: One of:
   - PROPOSES: Document introduces/proposes this method (usually the seminal paper)
   - EVALUATES: Document evaluates/benchmarks/compares this method
   - DESCRIBES: Document describes/explains this implementation
   - USES: Document uses or demonstrates this implementation
   - MENTIONS: Document briefly mentions but doesn't focus on it
3. evidence: A brief quote or reason (max 100 chars)
4. confidence: 0.0-1.0 based on how clearly it's mentioned

Also identify any NEW methods or implementations not in our KG that should be added.

Output ONLY valid JSON in this format:
{{
  "links": [
    {{"entity_id": "m:react", "relationship": "PROPOSES", "evidence": "We introduce ReAct...", "confidence": 0.95}},
    {{"entity_id": "impl:langchain", "relationship": "USES", "evidence": "implemented using LangChain", "confidence": 0.8}}
  ],
  "new_entities": [
    {{"type": "Method", "name": "NewMethod", "description": "brief description"}}
  ]
}}"""

        try:
            response = provider.generate(prompt, max_tokens=1000)
            result = self._parse_response(response, catalog)
            result.doc_id = doc.doc_id
            return result

        except Exception as e:
            print(f"[DocumentLinker] LLM extraction failed: {e}")
            return self._heuristic_link(doc, catalog)

    def _parse_response(self, response: str, catalog: dict) -> LinkingResult:
        """Parse LLM response into LinkingResult."""
        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            return LinkingResult(doc_id="", proposed_links=[], new_entities=[])

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return LinkingResult(doc_id="", proposed_links=[], new_entities=[])

        # Build entity lookup
        entity_lookup = {}
        for m in catalog.get("methods", []):
            entity_lookup[m["id"]] = {"name": m["name"], "type": "Method"}
        for i in catalog.get("implementations", []):
            entity_lookup[i["id"]] = {"name": i["name"], "type": "Implementation"}

        # Parse links
        proposed_links = []
        for link in data.get("links", []):
            entity_id = link.get("entity_id", "")
            if entity_id not in entity_lookup:
                continue

            entity_info = entity_lookup[entity_id]
            proposed_links.append(
                ProposedLink(
                    entity_id=entity_id,
                    entity_name=entity_info["name"],
                    entity_type=entity_info["type"],
                    relationship=link.get("relationship", "MENTIONS"),
                    evidence=link.get("evidence", "")[:200],
                    confidence=min(1.0, max(0.0, link.get("confidence", 0.5))),
                )
            )

        # Parse new entities
        new_entities = data.get("new_entities", [])

        return LinkingResult(
            doc_id="",
            proposed_links=proposed_links,
            new_entities=new_entities,
        )

    def _heuristic_link(self, doc: Document, catalog: dict) -> LinkingResult:
        """Fallback heuristic linking without LLM."""
        content_lower = doc.content.lower()
        title_lower = doc.title.lower()

        proposed_links = []

        # Check for method mentions
        for method in catalog.get("methods", []):
            name_lower = method["name"].lower()
            # Check if method name appears in title or content
            if name_lower in title_lower:
                proposed_links.append(
                    ProposedLink(
                        entity_id=method["id"],
                        entity_name=method["name"],
                        entity_type="Method",
                        relationship="PROPOSES" if "propose" in title_lower else "EVALUATES",
                        evidence=f"Mentioned in title: {doc.title[:50]}",
                        confidence=0.8,
                    )
                )
            elif name_lower in content_lower:
                # Count occurrences
                count = content_lower.count(name_lower)
                if count >= 3:
                    proposed_links.append(
                        ProposedLink(
                            entity_id=method["id"],
                            entity_name=method["name"],
                            entity_type="Method",
                            relationship="EVALUATES" if count >= 5 else "MENTIONS",
                            evidence=f"Mentioned {count} times in content",
                            confidence=min(0.7, 0.4 + count * 0.05),
                        )
                    )

        # Check for implementation mentions
        for impl in catalog.get("implementations", []):
            name_lower = impl["name"].lower()
            if name_lower in content_lower:
                count = content_lower.count(name_lower)
                if count >= 2:
                    proposed_links.append(
                        ProposedLink(
                            entity_id=impl["id"],
                            entity_name=impl["name"],
                            entity_type="Implementation",
                            relationship="USES" if count >= 3 else "MENTIONS",
                            evidence=f"Mentioned {count} times",
                            confidence=min(0.6, 0.3 + count * 0.1),
                        )
                    )

        return LinkingResult(
            doc_id=doc.doc_id,
            proposed_links=proposed_links[:10],  # Limit to 10
            new_entities=[],
        )

    def _load_entity_catalog(self) -> dict:
        """Load entity catalog from file or generate from Neo4j."""
        if self._entity_catalog is not None:
            return self._entity_catalog

        # Try to load from file
        catalog_path = Path(__file__).resolve().parents[2] / "data" / "entity_catalog.json"
        if catalog_path.exists():
            with open(catalog_path, "r", encoding="utf-8") as f:
                self._entity_catalog = json.load(f)
                return self._entity_catalog

        # Generate from Neo4j
        try:
            self._entity_catalog = self._generate_catalog_from_neo4j()
        except Exception as e:
            print(f"[DocumentLinker] Failed to load catalog: {e}")
            self._entity_catalog = {"methods": [], "implementations": []}

        return self._entity_catalog

    def _generate_catalog_from_neo4j(self) -> dict:
        """Generate entity catalog from Neo4j."""
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()

        # Get methods
        methods = client.run_cypher("""
            MATCH (m:Method)
            RETURN m.id AS id, m.name AS name, m.description AS description
            ORDER BY m.name
        """)

        # Get implementations
        implementations = client.run_cypher("""
            MATCH (i:Implementation)
            RETURN i.id AS id, i.name AS name, i.description AS description
            ORDER BY i.name
        """)

        client.close()

        return {
            "methods": [dict(m) for m in methods],
            "implementations": [dict(i) for i in implementations],
        }

    def save_document_to_kg(
        self,
        doc: Document,
        approved_links: list[ProposedLink],
    ) -> bool:
        """Save document node and approved relationships to Neo4j.

        Args:
            doc: Document to save.
            approved_links: List of approved links to create.

        Returns:
            True if successful.
        """
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()

        try:
            # Create document node
            doc_query = """
            MERGE (d:Document {id: $id})
            SET d.title = $title,
                d.doc_type = $doc_type,
                d.source_url = $source_url,
                d.source_path = $source_path,
                d.authors = $authors,
                d.year = $year,
                d.content_hash = $content_hash,
                d.created_at = datetime()
            """
            client.run_cypher(doc_query, {
                "id": doc.doc_id,
                "title": doc.title,
                "doc_type": doc.doc_type,
                "source_url": doc.source_url,
                "source_path": doc.source_path,
                "authors": doc.authors,
                "year": doc.year,
                "content_hash": doc.content_hash,
            })

            # Create relationships
            for link in approved_links:
                rel_type = link.relationship.upper()

                # Different query based on entity type
                if link.entity_type == "Method":
                    rel_query = f"""
                    MATCH (d:Document {{id: $doc_id}})
                    MATCH (m:Method {{id: $entity_id}})
                    MERGE (d)-[r:{rel_type}]->(m)
                    SET r.evidence = $evidence,
                        r.confidence = $confidence,
                        r.created_at = datetime()
                    """
                else:  # Implementation
                    rel_query = f"""
                    MATCH (d:Document {{id: $doc_id}})
                    MATCH (i:Implementation {{id: $entity_id}})
                    MERGE (d)-[r:{rel_type}]->(i)
                    SET r.evidence = $evidence,
                        r.confidence = $confidence,
                        r.created_at = datetime()
                    """

                client.run_cypher(rel_query, {
                    "doc_id": doc.doc_id,
                    "entity_id": link.entity_id,
                    "evidence": link.evidence,
                    "confidence": link.confidence,
                })

            client.close()
            return True

        except Exception as e:
            print(f"[DocumentLinker] Failed to save to Neo4j: {e}")
            client.close()
            return False
