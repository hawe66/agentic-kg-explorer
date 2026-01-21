"""Neo4j client for Knowledge Graph operations."""

from contextlib import contextmanager
from typing import Any, Generator
import logging

from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError

from config import get_settings
from .schema import (
    Document, Concept, Author, Source,
    Relationship, RelationType,
    MidCategory, SubCategory, DocumentType
)

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j database client with CRUD operations."""

    def __init__(self, uri: str | None = None, username: str | None = None, password: str | None = None):
        settings = get_settings()
        self._uri = uri or settings.neo4j_uri
        self._username = username or settings.neo4j_username
        self._password = password or settings.neo4j_password
        self._driver: Driver | None = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._username, self._password)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self._uri}")
        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise

    def close(self) -> None:
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        if not self._driver:
            self.connect()
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()

    # ========================================================================
    # Schema Setup
    # ========================================================================

    def setup_constraints(self) -> None:
        """Create uniqueness constraints and indexes."""
        constraints = [
            "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE",
        ]
        
        indexes = [
            "CREATE INDEX doc_title IF NOT EXISTS FOR (d:Document) ON (d.title)",
            "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX concept_category IF NOT EXISTS FOR (c:Concept) ON (c.category_mid, c.category_sub)",
        ]
        
        with self.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.debug(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.warning(f"Constraint may already exist: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.debug(f"Created index: {index}")
                except Exception as e:
                    logger.warning(f"Index may already exist: {e}")
        
        logger.info("Schema constraints and indexes set up")

    # ========================================================================
    # Document CRUD
    # ========================================================================

    def create_document(self, doc: Document) -> Document:
        """Create a Document node."""
        query = """
        CREATE (d:Document {
            id: $id,
            title: $title,
            doc_type: $doc_type,
            source_url: $source_url,
            summary: $summary,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at),
            authors: $authors,
            published_date: $published_date,
            tags: $tags
        })
        RETURN d
        """
        with self.session() as session:
            result = session.run(
                query,
                id=doc.id,
                title=doc.title,
                doc_type=doc.doc_type.value,
                source_url=doc.source_url,
                summary=doc.summary,
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
                authors=doc.authors,
                published_date=doc.published_date.isoformat() if doc.published_date else None,
                tags=doc.tags,
            )
            result.consume()
        logger.info(f"Created document: {doc.id}")
        return doc

    def get_document(self, doc_id: str) -> Document | None:
        """Get a Document by ID."""
        query = "MATCH (d:Document {id: $id}) RETURN d"
        with self.session() as session:
            result = session.run(query, id=doc_id)
            record = result.single()
            if record:
                node = record["d"]
                return Document(
                    id=node["id"],
                    title=node["title"],
                    doc_type=DocumentType(node["doc_type"]),
                    source_url=node.get("source_url"),
                    summary=node.get("summary"),
                    authors=node.get("authors", []),
                    tags=node.get("tags", []),
                )
        return None

    # ========================================================================
    # Concept CRUD
    # ========================================================================

    def create_concept(self, concept: Concept) -> Concept:
        """Create a Concept node."""
        query = """
        CREATE (c:Concept {
            id: $id,
            name: $name,
            aliases: $aliases,
            definition: $definition,
            category_mid: $category_mid,
            category_sub: $category_sub
        })
        RETURN c
        """
        with self.session() as session:
            session.run(
                query,
                id=concept.id,
                name=concept.name,
                aliases=concept.aliases,
                definition=concept.definition,
                category_mid=concept.category_mid.value,
                category_sub=concept.category_sub.value,
            )
        logger.info(f"Created concept: {concept.id} ({concept.name})")
        return concept

    def get_concept(self, concept_id: str) -> Concept | None:
        """Get a Concept by ID."""
        query = "MATCH (c:Concept {id: $id}) RETURN c"
        with self.session() as session:
            result = session.run(query, id=concept_id)
            record = result.single()
            if record:
                node = record["c"]
                return Concept(
                    id=node["id"],
                    name=node["name"],
                    aliases=node.get("aliases", []),
                    definition=node.get("definition"),
                    category_mid=MidCategory(node["category_mid"]),
                    category_sub=SubCategory(node["category_sub"]),
                )
        return None

    def find_concepts_by_category(
        self, 
        mid_category: MidCategory | None = None,
        sub_category: SubCategory | None = None
    ) -> list[Concept]:
        """Find concepts by category."""
        conditions = []
        params = {}
        
        if mid_category:
            conditions.append("c.category_mid = $mid")
            params["mid"] = mid_category.value
        if sub_category:
            conditions.append("c.category_sub = $sub")
            params["sub"] = sub_category.value
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"MATCH (c:Concept) {where_clause} RETURN c"
        
        concepts = []
        with self.session() as session:
            result = session.run(query, **params)
            for record in result:
                node = record["c"]
                concepts.append(Concept(
                    id=node["id"],
                    name=node["name"],
                    aliases=node.get("aliases", []),
                    definition=node.get("definition"),
                    category_mid=MidCategory(node["category_mid"]),
                    category_sub=SubCategory(node["category_sub"]),
                ))
        return concepts

    # ========================================================================
    # Author & Source CRUD
    # ========================================================================

    def create_author(self, author: Author) -> Author:
        """Create an Author node."""
        query = """
        MERGE (a:Author {id: $id})
        SET a.name = $name, a.affiliation = $affiliation
        RETURN a
        """
        with self.session() as session:
            session.run(query, id=author.id, name=author.name, affiliation=author.affiliation)
        logger.info(f"Created/updated author: {author.name}")
        return author

    def create_source(self, source: Source) -> Source:
        """Create a Source node."""
        query = """
        MERGE (s:Source {id: $id})
        SET s.name = $name, s.source_type = $source_type, s.url = $url
        RETURN s
        """
        with self.session() as session:
            session.run(
                query, 
                id=source.id, 
                name=source.name, 
                source_type=source.source_type,
                url=source.url
            )
        logger.info(f"Created/updated source: {source.name}")
        return source

    # ========================================================================
    # Relationships
    # ========================================================================

    def create_relationship(self, rel: Relationship) -> None:
        """Create a relationship between nodes."""
        # Determine node labels based on relationship type
        label_map = {
            RelationType.DISCUSSES: ("Document", "Concept"),
            RelationType.INTRODUCES: ("Document", "Concept"),
            RelationType.RELATED_TO: ("Concept", "Concept"),
            RelationType.PART_OF: ("Concept", "Concept"),
            RelationType.IMPLEMENTS: ("Concept", "Concept"),
            RelationType.COMPETES_WITH: ("Concept", "Concept"),
            RelationType.EXTENDS: ("Concept", "Concept"),
            RelationType.CITES: ("Document", "Document"),
            RelationType.DOC_EXTENDS: ("Document", "Document"),
            RelationType.CONTRADICTS: ("Document", "Document"),
            RelationType.AUTHORED_BY: ("Document", "Author"),
            RelationType.PUBLISHED_IN: ("Document", "Source"),
        }
        
        source_label, target_label = label_map.get(rel.rel_type, ("Node", "Node"))
        
        # Build properties string
        props_str = ", ".join(f"{k}: ${k}" for k in rel.properties.keys())
        props_clause = f" {{{props_str}}}" if props_str else ""
        
        query = f"""
        MATCH (a:{source_label} {{id: $source_id}})
        MATCH (b:{target_label} {{id: $target_id}})
        MERGE (a)-[r:{rel.rel_type.value}{props_clause}]->(b)
        RETURN r
        """
        
        with self.session() as session:
            session.run(
                query,
                source_id=rel.source_id,
                target_id=rel.target_id,
                **rel.properties
            )
        logger.info(f"Created relationship: {rel.source_id} -[{rel.rel_type.value}]-> {rel.target_id}")

    # ========================================================================
    # Query Methods
    # ========================================================================

    def search_documents(self, keyword: str, limit: int = 10) -> list[dict]:
        """Search documents by keyword in title or summary."""
        query = """
        MATCH (d:Document)
        WHERE d.title CONTAINS $keyword OR d.summary CONTAINS $keyword
        RETURN d.id AS id, d.title AS title, d.doc_type AS doc_type, d.summary AS summary
        LIMIT $limit
        """
        with self.session() as session:
            result = session.run(query, keyword=keyword, limit=limit)
            return [dict(record) for record in result]

    def get_document_with_concepts(self, doc_id: str) -> dict | None:
        """Get a document with all related concepts."""
        query = """
        MATCH (d:Document {id: $id})
        OPTIONAL MATCH (d)-[r:DISCUSSES|INTRODUCES]->(c:Concept)
        RETURN d, collect({concept: c, relation: type(r)}) AS concepts
        """
        with self.session() as session:
            result = session.run(query, id=doc_id)
            record = result.single()
            if record:
                doc_node = record["d"]
                concepts = [
                    {"concept": c["concept"], "relation": c["relation"]}
                    for c in record["concepts"]
                    if c["concept"] is not None
                ]
                return {
                    "document": dict(doc_node),
                    "concepts": concepts
                }
        return None

    def get_related_concepts(self, concept_id: str, depth: int = 2) -> list[dict]:
        """Get concepts related to a given concept up to specified depth."""
        query = """
        MATCH path = (c:Concept {id: $id})-[r:RELATED_TO|PART_OF|IMPLEMENTS|EXTENDS*1..$depth]-(related:Concept)
        RETURN related.id AS id, related.name AS name, 
               related.category_sub AS category,
               length(path) AS distance
        ORDER BY distance
        """
        with self.session() as session:
            result = session.run(query, id=concept_id, depth=depth)
            return [dict(record) for record in result]

    def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        """Run arbitrary Cypher query."""
        with self.session() as session:
            result = session.run(query, **(params or {}))
            return [dict(record) for record in result]

    # ========================================================================
    # Utility
    # ========================================================================

    def clear_database(self) -> None:
        """Clear all nodes and relationships. USE WITH CAUTION."""
        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.warning("Database cleared!")

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
            
            label_counts = {}
            for label in ["Document", "Concept", "Author", "Source"]:
                count = session.run(
                    f"MATCH (n:{label}) RETURN count(n) AS count"
                ).single()["count"]
                label_counts[label] = count
        
        return {
            "total_nodes": node_count,
            "total_relationships": rel_count,
            "nodes_by_label": label_counts
        }
