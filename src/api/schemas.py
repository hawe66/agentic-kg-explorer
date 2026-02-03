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
    """Vector search result with unified schema."""

    # Identity
    source_type: str        # "kg_node" | "web_search" | "paper"
    source_id: str          # node_id for KG, URL hash for web
    source_url: str | None  # URL for web results

    # KG linkage
    node_id: str | None
    node_label: str | None

    # Content
    title: str
    text: str
    score: float


class KgResultItem(BaseModel):
    """Flexible container for serialized Neo4j records."""

    class Config:
        extra = "allow"


class WebResultItem(BaseModel):
    """Web search result from Tavily."""

    title: str
    url: str
    content: str
    score: float


class QueryResponse(BaseModel):
    answer: str | None
    intent: str | None
    entities: list[str]
    confidence: float | None
    sources: list[SourceItem]
    vector_results: list[VectorResultItem]
    web_results: list[WebResultItem]
    web_query: str | None
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


# ---------------------------------------------------------------------------
# POST /graph/nodes/propose
# ---------------------------------------------------------------------------

class ProposeNodeRequest(BaseModel):
    """Request to propose a KG node from web content."""
    title: str = Field(..., description="Web result title")
    url: str = Field(..., description="Web result URL")
    content: str = Field(..., description="Web result content snippet")


class ProposedNodeResponse(BaseModel):
    """LLM-extracted node proposal."""
    node_type: str  # Method | Implementation | Document
    node_id: str
    name: str
    description: str

    # Optional fields based on node_type
    method_family: str | None = None
    method_type: str | None = None
    granularity: str | None = None
    addresses: list[dict] | None = None

    impl_type: str | None = None
    maintainer: str | None = None
    source_repo: str | None = None
    implements: list[dict] | None = None

    doc_type: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    proposes: list[str] | None = None

    source_url: str
    confidence: float


# ---------------------------------------------------------------------------
# POST /graph/nodes/approve
# ---------------------------------------------------------------------------

class ApproveNodeRequest(BaseModel):
    """Request to approve and create a proposed node."""
    node_type: str
    node_id: str
    name: str
    description: str

    method_family: str | None = None
    method_type: str | None = None
    granularity: str | None = None
    addresses: list[dict] | None = None

    impl_type: str | None = None
    maintainer: str | None = None
    source_repo: str | None = None
    implements: list[dict] | None = None

    doc_type: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    venue: str | None = None
    proposes: list[str] | None = None

    source_url: str


class ApproveNodeResponse(BaseModel):
    """Result of node approval."""
    success: bool
    node_id: str
    message: str
