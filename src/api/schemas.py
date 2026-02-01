"""Pydantic request/response models for the API."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question about the knowledge graph")
    llm_provider: str | None = Field(None, description="Override LLM provider (openai, anthropic, gemini)")
    llm_model: str | None = Field(None, description="Override LLM model name")


class SourceItem(BaseModel):
    type: str
    id: str
    name: str


class VectorResultItem(BaseModel):
    node_id: str
    node_label: str
    text: str
    field: str
    score: float


class KgResultItem(BaseModel):
    """Flexible container for serialized Neo4j records."""

    class Config:
        extra = "allow"


class QueryResponse(BaseModel):
    answer: str | None
    intent: str | None
    entities: list[str]
    confidence: float | None
    sources: list[SourceItem]
    vector_results: list[VectorResultItem]
    cypher_executed: list[str]
    kg_results: list[KgResultItem]
    error: str | None


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    neo4j: bool
    chromadb_entries: int


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

class StatsResponse(BaseModel):
    total_nodes: int
    total_relationships: int
    nodes_by_label: dict[str, int]
    relationships_by_type: dict[str, int]


# ---------------------------------------------------------------------------
# GET /graph/principles
# ---------------------------------------------------------------------------

class PrincipleItem(BaseModel):
    id: str
    name: str
    description: str
    method_count: int
    impl_count: int


class PrinciplesResponse(BaseModel):
    principles: list[PrincipleItem]
