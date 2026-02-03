"""KG Writer - Create nodes from web search results with user approval.

Flow:
1. propose_node() - LLM extracts entity from web content
2. approve_node() - User confirms, creates Neo4j node + VDB entry
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from config.settings import get_settings
from src.graph.client import Neo4jClient
from src.agents.providers.router import get_provider


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class WebResult(BaseModel):
    """Web search result to propose as KG node."""
    title: str
    url: str
    content: str


class ProposedNode(BaseModel):
    """LLM-extracted entity proposal."""
    node_type: str = Field(..., description="Method | Implementation | Document")
    node_id: str = Field(..., description="Proposed ID (e.g., m:new-method)")
    name: str
    description: str

    # Method-specific
    method_family: Optional[str] = None
    method_type: Optional[str] = None
    granularity: Optional[str] = None
    addresses: Optional[list[dict]] = None  # [{principle: "p:planning", role: "primary", weight: 1.0}]

    # Implementation-specific
    impl_type: Optional[str] = None
    maintainer: Optional[str] = None
    source_repo: Optional[str] = None
    implements: Optional[list[dict]] = None  # [{method: "m:react", level: "core"}]

    # Document-specific
    doc_type: Optional[str] = None
    authors: Optional[list[str]] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    proposes: Optional[list[str]] = None  # Method IDs this doc proposes

    # Source tracking
    source_url: str
    confidence: float = Field(default=0.7, description="LLM confidence in extraction")

    # Existing node info (for updates)
    exists_in_kg: bool = Field(default=False, description="Whether this entity already exists")
    existing_description: Optional[str] = None  # Current description in KG


class ApprovalResult(BaseModel):
    """Result of node approval."""
    success: bool
    node_id: str
    message: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are an expert at extracting structured knowledge from web content about AI agents and LLMs.

Given the following web search result, extract a knowledge graph node.

TITLE: {title}
URL: {url}
CONTENT:
{content}

Determine what type of entity this describes:
- Method: A technique, algorithm, or approach (e.g., ReAct, Chain-of-Thought, RAG)
- Implementation: A framework, library, or tool (e.g., LangChain, AutoGen, CrewAI)
- Document: A paper, article, or documentation

Extract the following as JSON:

```json
{{
  "node_type": "Method" | "Implementation" | "Document",
  "name": "Name of the entity",
  "description": "2-3 sentence description",

  // For Method:
  "method_family": "prompting_decoding | agent_loop_pattern | workflow_orchestration | retrieval_grounding | memory_system | reflection_verification | multi_agent_coordination | training_alignment | safety_control | evaluation | observability_tracing",
  "method_type": "prompt_pattern | decoding_strategy | search_planning_algo | agent_control_loop | workflow_pattern | retrieval_indexing | memory_architecture | coordination_pattern | training_objective | safety_classifier_or_policy | evaluation_protocol | instrumentation_pattern",
  "granularity": "atomic | composite",
  "addresses": [
    {{"principle": "p:planning | p:reasoning | p:memory | p:tool-use | p:reflection | p:grounding | p:learning | p:multi-agent | p:guardrails | p:tracing | p:perception", "role": "primary | secondary", "weight": 0.0-1.0}}
  ],

  // For Implementation:
  "impl_type": "framework | library | platform | service",
  "maintainer": "Organization or person",
  "source_repo": "GitHub URL if available",
  "implements": [
    {{"method": "m:method-id", "level": "core | first_class | template | integration | experimental"}}
  ],

  // For Document:
  "doc_type": "paper | article | documentation",
  "authors": ["Author 1", "Author 2"],
  "year": 2024,
  "venue": "Conference or journal name",
  "proposes": ["m:method-id"],

  "confidence": 0.0-1.0
}}
```

Only include fields relevant to the node_type. Be conservative with confidence - use 0.5-0.7 for uncertain extractions.

JSON response:"""


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def propose_node(web_result: WebResult) -> Optional[ProposedNode]:
    """Use LLM to extract a proposed KG node from web content.

    Args:
        web_result: Web search result with title, url, content

    Returns:
        ProposedNode if extraction successful, None otherwise
    """
    provider = get_provider()
    if provider is None:
        print("[KG Writer] No LLM provider available")
        return None

    prompt = EXTRACTION_PROMPT.format(
        title=web_result.title,
        url=web_result.url,
        content=web_result.content[:3000],  # Truncate long content
    )

    try:
        response = provider.generate(prompt, max_tokens=1000)

        # Extract JSON from response
        import json
        import re

        # Find JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                print(f"[KG Writer] Could not find JSON in response")
                return None

        data = json.loads(json_str)

        # Generate node ID
        node_type = data.get("node_type", "Method")
        name = data.get("name", "unknown")
        prefix = {"Method": "m:", "Implementation": "impl:", "Document": "doc:"}.get(node_type, "m:")
        slug = name.lower().replace(" ", "-").replace("_", "-")[:30]
        node_id = f"{prefix}{slug}"

        # Check if entity already exists in KG
        exists_in_kg = False
        existing_description = None
        try:
            existing = _check_existing_node(node_id, name, node_type)
            if existing:
                exists_in_kg = True
                node_id = existing["id"]  # Use existing ID
                existing_description = existing.get("description", "")
        except Exception as e:
            print(f"[KG Writer] Error checking existing node: {e}")

        return ProposedNode(
            node_type=node_type,
            node_id=node_id,
            name=name,
            description=data.get("description", ""),
            method_family=data.get("method_family"),
            method_type=data.get("method_type"),
            granularity=data.get("granularity"),
            addresses=data.get("addresses"),
            impl_type=data.get("impl_type"),
            maintainer=data.get("maintainer"),
            source_repo=data.get("source_repo"),
            implements=data.get("implements"),
            doc_type=data.get("doc_type"),
            authors=data.get("authors"),
            year=data.get("year"),
            venue=data.get("venue"),
            proposes=data.get("proposes"),
            source_url=web_result.url,
            confidence=data.get("confidence", 0.7),
            exists_in_kg=exists_in_kg,
            existing_description=existing_description,
        )

    except Exception as e:
        print(f"[KG Writer] Extraction error: {e}")
        return None


def _check_existing_node(node_id: str, name: str, node_type: str) -> Optional[dict]:
    """Check if a node already exists by ID or similar name.

    Returns existing node dict if found, None otherwise.
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
        # First check by exact ID
        result = client.run_cypher(
            "MATCH (n {id: $id}) RETURN n.id AS id, n.name AS name, n.description AS description",
            {"id": node_id}
        )
        if result:
            client.close()
            return result[0]

        # Then check by similar name (case-insensitive)
        label = {"Method": "Method", "Implementation": "Implementation", "Document": "Document"}.get(node_type, "Method")
        result = client.run_cypher(
            f"MATCH (n:{label}) WHERE toLower(n.name) = toLower($name) RETURN n.id AS id, n.name AS name, n.description AS description",
            {"name": name}
        )
        if result:
            client.close()
            return result[0]

        client.close()
        return None
    except Exception as e:
        client.close()
        raise e


def approve_node(proposed: ProposedNode, update_mode: bool = False) -> ApprovalResult:
    """Create or update a node in Neo4j and VDB.

    Args:
        proposed: User-approved node proposal
        update_mode: If True, update existing node instead of creating new

    Returns:
        ApprovalResult with success status
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
        # Check if node already exists
        check_query = "MATCH (n {id: $id}) RETURN n"
        existing = client.run_cypher(check_query, {"id": proposed.node_id})

        if existing and not update_mode:
            client.close()
            return ApprovalResult(
                success=False,
                node_id=proposed.node_id,
                message=f"Node {proposed.node_id} already exists. Use update mode to modify.",
            )

        if not existing and update_mode:
            client.close()
            return ApprovalResult(
                success=False,
                node_id=proposed.node_id,
                message=f"Node {proposed.node_id} not found. Cannot update non-existent node.",
            )

        # Create or update node based on type
        action = "Updated" if update_mode else "Created"
        if proposed.node_type == "Method":
            _upsert_method_node(client, proposed)
        elif proposed.node_type == "Implementation":
            _upsert_implementation_node(client, proposed)
        elif proposed.node_type == "Document":
            _upsert_document_node(client, proposed)
        else:
            client.close()
            return ApprovalResult(
                success=False,
                node_id=proposed.node_id,
                message=f"Unknown node type: {proposed.node_type}",
            )

        # Add/update VDB
        _add_to_vdb(proposed)

        # Update web search entry to link to node
        _update_web_entry(proposed)

        client.close()

        return ApprovalResult(
            success=True,
            node_id=proposed.node_id,
            message=f"{action} {proposed.node_type} node: {proposed.node_id}",
        )

    except Exception as e:
        client.close()
        return ApprovalResult(
            success=False,
            node_id=proposed.node_id,
            message=f"Error: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Neo4j Node Upsert (Create or Update)
# ---------------------------------------------------------------------------

def _upsert_method_node(client: Neo4jClient, proposed: ProposedNode) -> None:
    """Create or update Method node with ADDRESSES relationships."""
    query = """
    MERGE (m:Method {id: $id})
    SET m.name = $name,
        m.description = $description,
        m.method_family = $method_family,
        m.method_type = $method_type,
        m.granularity = $granularity,
        m.source_url = $source_url
    """
    client.run_cypher(query, {
        "id": proposed.node_id,
        "name": proposed.name,
        "description": proposed.description,
        "method_family": proposed.method_family or "",
        "method_type": proposed.method_type or "",
        "granularity": proposed.granularity or "atomic",
        "source_url": proposed.source_url,
    })

    # Merge ADDRESSES relationships
    for addr in (proposed.addresses or []):
        principle_id = addr.get("principle", "")
        if not principle_id:
            continue
        query = """
        MATCH (m:Method {id: $method_id})
        MATCH (p:Principle {id: $principle_id})
        MERGE (m)-[r:ADDRESSES]->(p)
        SET r.role = $role, r.weight = $weight
        """
        client.run_cypher(query, {
            "method_id": proposed.node_id,
            "principle_id": principle_id,
            "role": addr.get("role", "primary"),
            "weight": addr.get("weight", 1.0),
        })


def _upsert_implementation_node(client: Neo4jClient, proposed: ProposedNode) -> None:
    """Create or update Implementation node with IMPLEMENTS relationships."""
    query = """
    MERGE (i:Implementation {id: $id})
    SET i.name = $name,
        i.description = $description,
        i.impl_type = $impl_type,
        i.maintainer = $maintainer,
        i.source_repo = $source_repo,
        i.source_url = $source_url
    """
    client.run_cypher(query, {
        "id": proposed.node_id,
        "name": proposed.name,
        "description": proposed.description,
        "impl_type": proposed.impl_type or "",
        "maintainer": proposed.maintainer or "",
        "source_repo": proposed.source_repo or "",
        "source_url": proposed.source_url,
    })

    # Merge IMPLEMENTS relationships
    for impl in (proposed.implements or []):
        method_id = impl.get("method", "")
        if not method_id:
            continue
        query = """
        MATCH (i:Implementation {id: $impl_id})
        MATCH (m:Method {id: $method_id})
        MERGE (i)-[r:IMPLEMENTS]->(m)
        SET r.support_level = $level
        """
        client.run_cypher(query, {
            "impl_id": proposed.node_id,
            "method_id": method_id,
            "level": impl.get("level", "first_class"),
        })


def _upsert_document_node(client: Neo4jClient, proposed: ProposedNode) -> None:
    """Create or update Document node with PROPOSES relationships."""
    query = """
    MERGE (d:Document {id: $id})
    SET d.title = $name,
        d.abstract = $description,
        d.doc_type = $doc_type,
        d.authors = $authors,
        d.year = $year,
        d.venue = $venue,
        d.source_url = $source_url
    """
    client.run_cypher(query, {
        "id": proposed.node_id,
        "name": proposed.name,
        "description": proposed.description,
        "doc_type": proposed.doc_type or "paper",
        "authors": proposed.authors or [],
        "year": proposed.year,
        "venue": proposed.venue or "",
        "source_url": proposed.source_url,
    })

    # Merge PROPOSES relationships
    for method_id in (proposed.proposes or []):
        query = """
        MATCH (d:Document {id: $doc_id})
        MATCH (m:Method {id: $method_id})
        MERGE (d)-[:PROPOSES]->(m)
        """
        client.run_cypher(query, {
            "doc_id": proposed.node_id,
            "method_id": method_id,
        })


# ---------------------------------------------------------------------------
# VDB Operations
# ---------------------------------------------------------------------------

def _add_to_vdb(proposed: ProposedNode) -> None:
    """Add the new node to ChromaDB."""
    try:
        from src.retrieval.embedder import get_embedding_client
        from src.retrieval.vector_store import get_vector_store

        embedder = get_embedding_client()
        store = get_vector_store()

        if embedder is None:
            print("[KG Writer] No embedder available, skipping VDB")
            return

        # Build unified text
        lines = [f"[{proposed.node_type}] {proposed.name}"]
        lines.append(f"Description: {proposed.description}")

        if proposed.node_type == "Method":
            if proposed.method_family:
                lines.append(f"Family: {proposed.method_family}")
            if proposed.addresses:
                principles = [a["principle"] for a in proposed.addresses if a.get("principle")]
                if principles:
                    lines.append(f"Addresses: {', '.join(principles)}")
        elif proposed.node_type == "Implementation":
            if proposed.impl_type:
                lines.append(f"Type: {proposed.impl_type}")
            if proposed.maintainer:
                lines.append(f"Maintainer: {proposed.maintainer}")
        elif proposed.node_type == "Document":
            if proposed.authors:
                lines.append(f"Authors: {', '.join(proposed.authors)}")
            if proposed.year:
                lines.append(f"Year: {proposed.year}")

        text = "\n".join(lines)
        embedding = embedder.embed_single(text)

        collected_at = datetime.now(timezone.utc).isoformat()

        store.upsert(
            ids=[f"kg:{proposed.node_id}"],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "source_type": "kg_node",
                "source_id": proposed.node_id,
                "source_url": proposed.source_url,
                "collected_at": collected_at,
                "collector": "kg_writer",
                "node_id": proposed.node_id,
                "node_label": proposed.node_type,
                "title": proposed.name,
                "chunk_index": 0,
                "total_chunks": 1,
            }],
        )
        print(f"[KG Writer] Added {proposed.node_id} to VDB")

    except Exception as e:
        print(f"[KG Writer] VDB error: {e}")


def _update_web_entry(proposed: ProposedNode) -> None:
    """Update the web search VDB entry to link to the new KG node."""
    try:
        from src.retrieval.vector_store import get_vector_store

        store = get_vector_store()

        # Find web entries with matching URL
        url_hash = hashlib.md5(proposed.source_url.encode()).hexdigest()[:12]
        prefix = f"web:{url_hash}"

        # Get existing entries
        results = store._collection.get(
            where={"source_url": proposed.source_url},
            include=["metadatas"],
        )

        if not results["ids"]:
            return

        # Update metadata to link to new node
        for entry_id, metadata in zip(results["ids"], results["metadatas"]):
            metadata["node_id"] = proposed.node_id
            metadata["node_label"] = proposed.node_type
            store._collection.update(
                ids=[entry_id],
                metadatas=[metadata],
            )

        print(f"[KG Writer] Updated {len(results['ids'])} web entries to link to {proposed.node_id}")

    except Exception as e:
        print(f"[KG Writer] Web entry update error: {e}")
