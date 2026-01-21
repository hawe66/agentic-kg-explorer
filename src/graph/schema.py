"""Domain schema definitions for Agentic AI Knowledge Graph."""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Category Taxonomy
# ============================================================================

class MidCategory(str, Enum):
    """중분류 - Agentic AI 도메인"""
    ARCHITECTURE = "Architecture"
    REASONING = "Reasoning"
    GROUNDING = "Grounding"
    EVALUATION = "Evaluation"
    INDUSTRY = "Industry"


class SubCategory(str, Enum):
    """소분류"""
    # Architecture
    MULTI_AGENT_SYSTEMS = "Multi-Agent Systems"
    AGENT_ORCHESTRATION = "Agent Orchestration"
    MEMORY_AND_STATE = "Memory & State"
    TOOL_USE = "Tool Use & Function Calling"
    
    # Reasoning
    PLANNING = "Planning & Decomposition"
    SELF_REFLECTION = "Self-Reflection"
    COT_VARIANTS = "Chain-of-Thought Variants"
    
    # Grounding
    RAG = "RAG & Retrieval"
    KNOWLEDGE_GRAPHS = "Knowledge Graphs"
    WEB_API_INTEGRATION = "Web & API Integration"
    
    # Evaluation
    BENCHMARKS = "Benchmarks"
    SAFETY_ALIGNMENT = "Safety & Alignment"
    HUMAN_AGENT_INTERACTION = "Human-Agent Interaction"
    
    # Industry
    ENTERPRISE = "Enterprise Applications"
    DEVELOPER_TOOLS = "Developer Tools"
    DOMAIN_SPECIFIC = "Domain-Specific"


# Mapping: SubCategory -> MidCategory
SUB_TO_MID_CATEGORY: dict[SubCategory, MidCategory] = {
    SubCategory.MULTI_AGENT_SYSTEMS: MidCategory.ARCHITECTURE,
    SubCategory.AGENT_ORCHESTRATION: MidCategory.ARCHITECTURE,
    SubCategory.MEMORY_AND_STATE: MidCategory.ARCHITECTURE,
    SubCategory.TOOL_USE: MidCategory.ARCHITECTURE,
    
    SubCategory.PLANNING: MidCategory.REASONING,
    SubCategory.SELF_REFLECTION: MidCategory.REASONING,
    SubCategory.COT_VARIANTS: MidCategory.REASONING,
    
    SubCategory.RAG: MidCategory.GROUNDING,
    SubCategory.KNOWLEDGE_GRAPHS: MidCategory.GROUNDING,
    SubCategory.WEB_API_INTEGRATION: MidCategory.GROUNDING,
    
    SubCategory.BENCHMARKS: MidCategory.EVALUATION,
    SubCategory.SAFETY_ALIGNMENT: MidCategory.EVALUATION,
    SubCategory.HUMAN_AGENT_INTERACTION: MidCategory.EVALUATION,
    
    SubCategory.ENTERPRISE: MidCategory.INDUSTRY,
    SubCategory.DEVELOPER_TOOLS: MidCategory.INDUSTRY,
    SubCategory.DOMAIN_SPECIFIC: MidCategory.INDUSTRY,
}


class DocumentType(str, Enum):
    """문서 타입"""
    PAPER = "paper"
    ARTICLE = "article"
    MEMO = "memo"
    NEWS = "news"
    CODE = "code"


# ============================================================================
# Node Models
# ============================================================================

class Document(BaseModel):
    """문서 노드 모델"""
    id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    doc_type: DocumentType = Field(..., description="Type of document")
    source_url: str | None = Field(None, description="Original source URL")
    summary: str | None = Field(None, description="Brief summary")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Metadata
    authors: list[str] = Field(default_factory=list)
    published_date: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class Concept(BaseModel):
    """개념 노드 모델"""
    id: str = Field(..., description="Unique concept ID")
    name: str = Field(..., description="Concept name")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    definition: str | None = Field(None, description="Concept definition")
    category_mid: MidCategory = Field(..., description="Mid-level category")
    category_sub: SubCategory = Field(..., description="Sub-level category")


class Author(BaseModel):
    """저자 노드 모델"""
    id: str = Field(..., description="Unique author ID")
    name: str = Field(..., description="Author name")
    affiliation: str | None = Field(None, description="Organization/Institution")


class Source(BaseModel):
    """출처 노드 모델"""
    id: str = Field(..., description="Unique source ID")
    name: str = Field(..., description="Source name (e.g., arXiv, OpenAI Blog)")
    source_type: str = Field(..., description="Type: arxiv, blog, news, github, etc.")
    url: str | None = Field(None, description="Base URL")


# ============================================================================
# Relationship Models
# ============================================================================

class RelationType(str, Enum):
    """관계 타입"""
    # Document <-> Concept
    DISCUSSES = "DISCUSSES"
    INTRODUCES = "INTRODUCES"
    
    # Concept <-> Concept
    RELATED_TO = "RELATED_TO"
    PART_OF = "PART_OF"
    IMPLEMENTS = "IMPLEMENTS"
    COMPETES_WITH = "COMPETES_WITH"
    EXTENDS = "EXTENDS"
    
    # Document <-> Document
    CITES = "CITES"
    DOC_EXTENDS = "DOC_EXTENDS"
    CONTRADICTS = "CONTRADICTS"
    
    # Meta relationships
    AUTHORED_BY = "AUTHORED_BY"
    PUBLISHED_IN = "PUBLISHED_IN"


class Relationship(BaseModel):
    """관계 모델"""
    source_id: str
    target_id: str
    rel_type: RelationType
    properties: dict = Field(default_factory=dict)
