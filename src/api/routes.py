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

    if request.llm_provider:
        settings.llm_provider = request.llm_provider
        overridden = True
    if request.llm_model:
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
        cypher_executed=result.get("cypher_executed") or [],
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
