"""FastAPI route handlers."""

from fastapi import APIRouter, HTTPException

from config.settings import get_settings, reset_settings
from src.agents import run_agent
from src.graph.client import Neo4jClient
from src.retrieval.vector_store import get_vector_store

from .schemas import (
    HealthResponse,
    PrincipleItem,
    PrinciplesResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
    StatsResponse,
    VectorResultItem,
    WebResultItem,
    KgResultItem,
    ProposeNodeRequest,
    ProposedNodeResponse,
    ApproveNodeRequest,
    ApproveNodeResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_neo4j_client() -> Neo4jClient:
    settings = get_settings()
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    client.connect()
    return client


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    """Run the agent pipeline on a user query."""

    # Apply provider/model overrides if given
    overridden = False
    settings = get_settings()
    original_provider = settings.llm_provider
    original_model = settings.llm_model

    if request.llm_provider and request.llm_provider != "string":
        settings.llm_provider = request.llm_provider
        overridden = True
    if request.llm_model and request.llm_model != "string":
        settings.llm_model = request.llm_model
        overridden = True

    try:
        result = run_agent(request.query)
    finally:
        # Restore original settings
        if overridden:
            settings.llm_provider = original_provider
            settings.llm_model = original_model

    return QueryResponse(
        answer=result.get("answer"),
        intent=result.get("intent"),
        entities=result.get("entities") or [],
        confidence=result.get("confidence"),
        sources=[
            SourceItem(**s) for s in (result.get("sources") or [])
        ],
        vector_results=[
            VectorResultItem(**v) for v in (result.get("vector_results") or [])
        ],
        web_results=[
            WebResultItem(**w) for w in (result.get("web_results") or [])
        ],
        web_query=result.get("web_query"),
        cypher_executed=result.get("cypher_executed") or [],
        kg_results=[
            KgResultItem(**k) for k in (result.get("kg_results") or [])
        ],
        error=result.get("error"),
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Check service health: Neo4j connectivity and ChromaDB status."""
    neo4j_ok = False
    try:
        client = _get_neo4j_client()
        client.close()
        neo4j_ok = True
    except Exception:
        pass

    chroma_count = 0
    try:
        store = get_vector_store()
        chroma_count = store.count
    except Exception:
        pass

    return HealthResponse(
        status="ok" if neo4j_ok else "degraded",
        neo4j=neo4j_ok,
        chromadb_entries=chroma_count,
    )


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get Neo4j database statistics."""
    try:
        client = _get_neo4j_client()
        stats = client.get_stats()
        client.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")

    return StatsResponse(
        total_nodes=stats.total_nodes,
        total_relationships=stats.total_relationships,
        nodes_by_label=stats.nodes_by_label,
        relationships_by_type=stats.relationships_by_type,
    )


# ---------------------------------------------------------------------------
# GET /graph/principles
# ---------------------------------------------------------------------------

@router.get("/graph/principles", response_model=PrinciplesResponse)
def get_principles():
    """List all 11 principles with method and implementation counts."""
    try:
        client = _get_neo4j_client()
        # Custom query that returns id, name, description, counts
        rows = client.run_cypher("""
            MATCH (p:Principle)
            OPTIONAL MATCH (p)<-[:ADDRESSES]-(m:Method)
            OPTIONAL MATCH (m)<-[:IMPLEMENTS]-(i:Implementation)
            RETURN p.id AS id, p.name AS name, p.description AS description,
                   count(DISTINCT m) AS method_count,
                   count(DISTINCT i) AS impl_count
            ORDER BY p.name
        """)
        client.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")

    principles = [
        PrincipleItem(
            id=row["id"],
            name=row["name"],
            description=row.get("description") or "",
            method_count=row["method_count"],
            impl_count=row["impl_count"],
        )
        for row in rows
    ]

    return PrinciplesResponse(principles=principles)


# ---------------------------------------------------------------------------
# POST /graph/nodes/propose
# ---------------------------------------------------------------------------

@router.post("/graph/nodes/propose", response_model=ProposedNodeResponse)
def propose_node(request: ProposeNodeRequest):
    """Use LLM to extract a KG node proposal from web content.

    This is step 1 of adding web content to the KG.
    The response can be reviewed and modified before approval.
    """
    from .kg_writer import propose_node as _propose_node, WebResult

    web_result = WebResult(
        title=request.title,
        url=request.url,
        content=request.content,
    )

    proposed = _propose_node(web_result)

    if proposed is None:
        raise HTTPException(
            status_code=422,
            detail="Could not extract entity from web content",
        )

    return ProposedNodeResponse(
        node_type=proposed.node_type,
        node_id=proposed.node_id,
        name=proposed.name,
        description=proposed.description,
        method_family=proposed.method_family,
        method_type=proposed.method_type,
        granularity=proposed.granularity,
        addresses=proposed.addresses,
        impl_type=proposed.impl_type,
        maintainer=proposed.maintainer,
        source_repo=proposed.source_repo,
        implements=proposed.implements,
        doc_type=proposed.doc_type,
        authors=proposed.authors,
        year=proposed.year,
        venue=proposed.venue,
        proposes=proposed.proposes,
        source_url=proposed.source_url,
        confidence=proposed.confidence,
    )


# ---------------------------------------------------------------------------
# POST /graph/nodes/approve
# ---------------------------------------------------------------------------

@router.post("/graph/nodes/approve", response_model=ApproveNodeResponse)
def approve_node(request: ApproveNodeRequest):
    """Approve and create a proposed node in Neo4j and VDB.

    This is step 2 of adding web content to the KG.
    The request should contain the (possibly modified) proposal from step 1.
    """
    from .kg_writer import approve_node as _approve_node, ProposedNode

    proposed = ProposedNode(
        node_type=request.node_type,
        node_id=request.node_id,
        name=request.name,
        description=request.description,
        method_family=request.method_family,
        method_type=request.method_type,
        granularity=request.granularity,
        addresses=request.addresses,
        impl_type=request.impl_type,
        maintainer=request.maintainer,
        source_repo=request.source_repo,
        implements=request.implements,
        doc_type=request.doc_type,
        authors=request.authors,
        year=request.year,
        venue=request.venue,
        proposes=request.proposes,
        source_url=request.source_url,
    )

    result = _approve_node(proposed)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return ApproveNodeResponse(
        success=result.success,
        node_id=result.node_id,
        message=result.message,
    )
