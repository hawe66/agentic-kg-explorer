"""
Agentic AI Knowledge Graph - Neo4j Client

Database client for the Agentic AI Knowledge Graph.
Supports cypher file execution, CRUD operations, and domain-specific queries.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

from neo4j import GraphDatabase, Driver, Session, TrustAll
from neo4j.exceptions import ServiceUnavailable, AuthError

from config import get_settings
from .schema import StatsResult

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j database client with KG operations."""

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        settings = get_settings()
        self._uri = uri or settings.neo4j_uri
        self._username = username or settings.neo4j_username
        self._password = password or settings.neo4j_password
        self._database = database or getattr(settings, "neo4j_database", "neo4j")
        self._driver: Optional[Driver] = None

    # ========================================================================
    # Connection Management
    # ========================================================================

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._username, self._password),
                encrypted=True,
                trusted_certificates=TrustAll()  # SSL 검증 비활성화
            )
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
            self._driver = None
            logger.info("Neo4j connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def driver(self) -> Driver:
        """Get driver, connecting if needed."""
        if self._driver is None:
            self.connect()
        return self._driver

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        session = self.driver.session(database=self._database)
        try:
            yield session
        finally:
            session.close()

    # ========================================================================
    # Cypher File Execution
    # ========================================================================

    def run_cypher_file(self, filepath: Path) -> int:
        """
        Execute a Cypher file containing multiple statements.

        Args:
            filepath: Path to the .cypher file

        Returns:
            Number of statements executed
        """
        logger.info(f"Running Cypher file: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse statements (skip comments, split by semicolon)
        statements = []
        current = []

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//") or not stripped:
                continue
            current.append(line)
            if stripped.endswith(";"):
                stmt = "\n".join(current).strip().rstrip(";")
                if stmt:
                    statements.append(stmt)
                current = []

        # Handle remaining statement without semicolon
        if current:
            stmt = "\n".join(current).strip().rstrip(";")
            if stmt:
                statements.append(stmt)

        # Execute statements
        with self.session() as session:
            for i, stmt in enumerate(statements, 1):
                try:
                    session.run(stmt)
                    logger.debug(f"Executed statement {i}/{len(statements)}")
                except Exception as e:
                    logger.warning(f"Statement {i} failed: {e}")
                    logger.debug(f"Statement: {stmt[:100]}...")

        logger.info(f"Completed {len(statements)} statements from {filepath.name}")
        return len(statements)

    # ========================================================================
    # Schema & Seed Data
    # ========================================================================

    def setup_schema(self, schema_file: Optional[Path] = None) -> int:
        """
        Set up database schema (constraints, indexes).

        Args:
            schema_file: Path to schema.cypher (default: neo4j/schema.cypher)

        Returns:
            Number of statements executed
        """
        if schema_file is None:
            schema_file = Path(__file__).parent.parent.parent / "neo4j" / "schema.cypher"

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        logger.info("Setting up database schema...")
        count = self.run_cypher_file(schema_file)
        logger.info("Schema setup complete")
        return count

    def load_seed_data(self, seed_file: Optional[Path] = None) -> int:
        """
        Load seed data into database.

        Args:
            seed_file: Path to seed_data.cypher (default: neo4j/seed_data.cypher)

        Returns:
            Number of statements executed
        """
        if seed_file is None:
            seed_file = Path(__file__).parent.parent.parent / "neo4j" / "seed_data.cypher"

        if not seed_file.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")

        logger.info("Loading seed data...")
        count = self.run_cypher_file(seed_file)
        logger.info("Seed data loaded")
        return count

    def clear_database(self) -> None:
        """Clear all nodes and relationships. USE WITH CAUTION."""
        logger.warning("Clearing all data from database!")
        with self.session() as session:
            session.run("MATCH ()-[r]->() DELETE r")
            session.run("MATCH (n) DELETE n")
        logger.info("Database cleared")

    def initialize(self, clear_first: bool = False) -> StatsResult:
        """
        Full database initialization: schema + seed data.

        Args:
            clear_first: If True, clear database before initialization

        Returns:
            Database statistics after initialization
        """
        logger.info("Starting database initialization...")

        if clear_first:
            self.clear_database()

        self.setup_schema()
        self.load_seed_data()

        stats = self.get_stats()
        logger.info(f"Initialization complete: {stats.total_nodes} nodes, {stats.total_relationships} relationships")
        return stats

    # ========================================================================
    # Raw Cypher Execution
    # ========================================================================

    def run_cypher(self, query: str, params: Optional[dict] = None) -> list[dict]:
        """Execute arbitrary Cypher query."""
        with self.session() as session:
            result = session.run(query, **(params or {}))
            return [dict(record) for record in result]

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_stats(self) -> StatsResult:
        """Get database statistics."""
        with self.session() as session:
            # Node counts by label
            result = session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count"
            )
            nodes_by_label = {r["label"]: r["count"] for r in result}

            # Relationship counts by type
            result = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count"
            )
            rels_by_type = {r["type"]: r["count"] for r in result}

        return StatsResult(
            total_nodes=sum(nodes_by_label.values()),
            total_relationships=sum(rels_by_type.values()),
            nodes_by_label=nodes_by_label,
            relationships_by_type=rels_by_type,
        )

    # ========================================================================
    # Domain Queries - Principle/Method/Implementation
    # ========================================================================

    def get_principle_method_impl_paths(self) -> list[dict]:
        """
        Get full Principle → Method → Implementation paths.

        Returns:
            List of {principle, method, implementations} dicts
        """
        query = """
        MATCH path = (p:Principle)<-[:ADDRESSES]-(m:Method)<-[:IMPLEMENTS]-(i:Implementation)
        RETURN p.name AS principle,
               m.name AS method,
               collect(DISTINCT i.name) AS implementations
        ORDER BY p.name, m.name
        """
        return self.run_cypher(query)

    def get_methods_by_principle(self, principle_id: str) -> list[dict]:
        """
        Get all methods addressing a specific principle.

        Args:
            principle_id: Principle ID (e.g., 'p:reasoning')

        Returns:
            List of method details with ADDRESSES relationship properties
        """
        query = """
        MATCH (p:Principle {id: $principle_id})<-[a:ADDRESSES]-(m:Method)
        RETURN m.id AS id, m.name AS name, m.method_family AS family,
               a.role AS role, a.weight AS weight
        ORDER BY a.weight DESC, m.name
        """
        return self.run_cypher(query, {"principle_id": principle_id})

    def get_implementations_by_method(self, method_id: str) -> list[dict]:
        """
        Get all implementations of a specific method.

        Args:
            method_id: Method ID (e.g., 'm:react')

        Returns:
            List of implementation details with IMPLEMENTS relationship properties
        """
        query = """
        MATCH (m:Method {id: $method_id})<-[r:IMPLEMENTS]-(i:Implementation)
        RETURN i.id AS id, i.name AS name, i.impl_type AS impl_type,
               r.support_level AS support_level, r.evidence AS evidence
        ORDER BY r.support_level, i.name
        """
        return self.run_cypher(query, {"method_id": method_id})

    def get_principles_coverage(self) -> list[dict]:
        """
        Get coverage of each principle (methods + implementations count).

        Returns:
            List of {principle, method_count, impl_count} dicts
        """
        query = """
        MATCH (p:Principle)
        OPTIONAL MATCH (p)<-[:ADDRESSES]-(m:Method)
        OPTIONAL MATCH (m)<-[:IMPLEMENTS]-(i:Implementation)
        RETURN p.name AS principle,
               count(DISTINCT m) AS method_count,
               count(DISTINCT i) AS impl_count
        ORDER BY method_count DESC
        """
        return self.run_cypher(query)

    # ========================================================================
    # Domain Queries - Standards
    # ========================================================================

    def get_standard_compliance(self) -> list[dict]:
        """
        Get standard compliance status across implementations.

        Returns:
            List of compliance relationships with details
        """
        query = """
        MATCH (i:Implementation)-[r:COMPLIES_WITH]->(sv:StandardVersion)
              <-[:HAS_VERSION]-(s:Standard)
        RETURN s.name AS standard,
               sv.version AS version,
               i.name AS implementation,
               r.role AS role,
               r.level AS level
        ORDER BY s.name, i.name
        """
        return self.run_cypher(query)

    # ========================================================================
    # Domain Queries - Methods
    # ========================================================================

    def get_method_family_distribution(self) -> list[dict]:
        """Get distribution of methods by family."""
        query = """
        MATCH (m:Method)
        RETURN m.method_family AS family, count(*) AS count
        ORDER BY count DESC
        """
        return self.run_cypher(query)

    def get_composite_methods(self) -> list[dict]:
        """Get composite methods and their components."""
        query = """
        MATCH (composite:Method {granularity: 'composite'})-[:USES]->(component:Method)
        RETURN composite.name AS composite_method,
               collect(component.name) AS components
        ORDER BY composite.name
        """
        return self.run_cypher(query)

    def search_methods(self, keyword: str, limit: int = 10) -> list[dict]:
        """
        Search methods by keyword in name or description.

        Args:
            keyword: Search term
            limit: Maximum results

        Returns:
            List of matching methods
        """
        query = """
        MATCH (m:Method)
        WHERE m.name CONTAINS $keyword OR m.description CONTAINS $keyword
        RETURN m.id AS id, m.name AS name, m.method_family AS family,
               m.description AS description
        LIMIT $limit
        """
        return self.run_cypher(query, {"keyword": keyword, "limit": limit})

    # ========================================================================
    # Validation Queries
    # ========================================================================

    def get_orphan_methods(self) -> list[dict]:
        """Find methods not linked to any Principle."""
        query = """
        MATCH (m:Method)
        WHERE NOT (m)-[:ADDRESSES]->(:Principle)
        RETURN m.id AS id, m.name AS name
        ORDER BY m.name
        """
        return self.run_cypher(query)

    def get_orphan_implementations(self) -> list[dict]:
        """Find implementations not linked to any Method."""
        query = """
        MATCH (i:Implementation)
        WHERE NOT (i)-[:IMPLEMENTS]->(:Method)
        RETURN i.id AS id, i.name AS name
        ORDER BY i.name
        """
        return self.run_cypher(query)

    def get_methods_without_paper(self) -> list[dict]:
        """Find methods without a proposing paper or seminal_source."""
        query = """
        MATCH (m:Method)
        WHERE NOT (m)<-[:PROPOSES]-(:Document:Paper)
          AND m.seminal_source IS NULL
        RETURN m.id AS id, m.name AS name, m.year_introduced AS year
        ORDER BY m.name
        """
        return self.run_cypher(query)

    def get_uncovered_principles(self) -> list[dict]:
        """Find principles with no methods addressing them."""
        query = """
        MATCH (p:Principle)
        WHERE NOT (p)<-[:ADDRESSES]-(:Method)
        RETURN p.id AS id, p.name AS name
        """
        return self.run_cypher(query)

    # ========================================================================
    # Node Operations
    # ========================================================================

    def get_node(self, label: str, node_id: str) -> Optional[dict]:
        """
        Get a node by label and ID.

        Args:
            label: Node label (e.g., 'Method', 'Implementation')
            node_id: Node ID

        Returns:
            Node properties as dict, or None if not found
        """
        query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
        results = self.run_cypher(query, {"id": node_id})
        if results:
            return dict(results[0]["n"])
        return None

    def get_all_nodes(self, label: str) -> list[dict]:
        """
        Get all nodes of a given label.

        Args:
            label: Node label (e.g., 'Principle', 'Method')

        Returns:
            List of node properties
        """
        query = f"MATCH (n:{label}) RETURN n ORDER BY n.name"
        results = self.run_cypher(query)
        return [dict(r["n"]) for r in results]

    def create_node(self, label: str, properties: dict) -> dict:
        """
        Create a node with given label and properties.

        Args:
            label: Node label
            properties: Node properties (must include 'id')

        Returns:
            Created node properties
        """
        props_str = ", ".join(f"{k}: ${k}" for k in properties.keys())
        query = f"CREATE (n:{label} {{{props_str}}}) RETURN n"
        results = self.run_cypher(query, properties)
        return dict(results[0]["n"])

    def create_relationship(
        self,
        source_label: str,
        source_id: str,
        rel_type: str,
        target_label: str,
        target_id: str,
        properties: Optional[dict] = None,
    ) -> None:
        """
        Create a relationship between two nodes.

        Args:
            source_label: Source node label
            source_id: Source node ID
            rel_type: Relationship type
            target_label: Target node label
            target_id: Target node ID
            properties: Optional relationship properties
        """
        props = properties or {}
        props_str = ", ".join(f"{k}: ${k}" for k in props.keys())
        props_clause = f" {{{props_str}}}" if props_str else ""

        query = f"""
        MATCH (a:{source_label} {{id: $source_id}})
        MATCH (b:{target_label} {{id: $target_id}})
        MERGE (a)-[r:{rel_type}{props_clause}]->(b)
        RETURN r
        """
        self.run_cypher(query, {"source_id": source_id, "target_id": target_id, **props})
