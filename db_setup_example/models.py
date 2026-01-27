"""
Agentic AI Knowledge Graph - Pydantic Models

노드 타입별 데이터 모델 정의.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class StandardType(str, Enum):
    PROTOCOL = "protocol"
    SEMANTIC_CONVENTION = "semantic_convention"
    SCHEMA = "schema"
    GUIDELINE = "guideline"


class GovernanceType(str, Enum):
    COMPANY = "company"
    FOUNDATION = "foundation"
    COMMUNITY = "community"


class StatusType(str, Enum):
    DRAFT = "draft"
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class VersioningScheme(str, Enum):
    SEMVER = "semver"
    DATE = "date"
    OTHER = "other"


class MethodFamily(str, Enum):
    PROMPTING_DECODING = "prompting_decoding"
    AGENT_LOOP_PATTERN = "agent_loop_pattern"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    RETRIEVAL_GROUNDING = "retrieval_grounding"
    MEMORY_SYSTEM = "memory_system"
    REFLECTION_VERIFICATION = "reflection_verification"
    MULTI_AGENT_COORDINATION = "multi_agent_coordination"
    TRAINING_ALIGNMENT = "training_alignment"
    SAFETY_CONTROL = "safety_control"
    EVALUATION = "evaluation"
    OBSERVABILITY_TRACING = "observability_tracing"


class MethodType(str, Enum):
    PROMPT_PATTERN = "prompt_pattern"
    DECODING_STRATEGY = "decoding_strategy"
    SEARCH_PLANNING_ALGO = "search_planning_algo"
    AGENT_CONTROL_LOOP = "agent_control_loop"
    WORKFLOW_PATTERN = "workflow_pattern"
    RETRIEVAL_INDEXING = "retrieval_indexing"
    MEMORY_ARCHITECTURE = "memory_architecture"
    COORDINATION_PATTERN = "coordination_pattern"
    TRAINING_OBJECTIVE = "training_objective"
    SAFETY_CLASSIFIER_OR_POLICY = "safety_classifier_or_policy"
    EVALUATION_PROTOCOL = "evaluation_protocol"
    INSTRUMENTATION_PATTERN = "instrumentation_pattern"


class Granularity(str, Enum):
    ATOMIC = "atomic"
    COMPOSITE = "composite"


class Maturity(str, Enum):
    RESEARCH = "research"
    PRODUCTION = "production"
    STANDARDIZED = "standardized"
    LEGACY = "legacy"


class ImplType(str, Enum):
    FRAMEWORK = "framework"
    SDK = "sdk"
    LIBRARY = "library"
    SERVICE = "service"
    MODEL = "model"
    TOOL = "tool"


class Distribution(str, Enum):
    OSS = "oss"
    MANAGED = "managed"
    HOSTED_MODEL = "hosted_model"
    INTERNAL = "internal"


class DocType(str, Enum):
    PAPER = "paper"
    SPEC = "spec"
    GUIDE = "guide"
    BLOG = "blog"
    REPO = "repo"


class Stance(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    MENTIONS = "mentions"


class AddressRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class SupportLevel(str, Enum):
    CORE = "core"
    FIRST_CLASS = "first_class"
    TEMPLATE = "template"
    INTEGRATION = "integration"
    EXPERIMENTAL = "experimental"


class EvidenceType(str, Enum):
    DOC = "doc"
    CODE = "code"
    BOTH = "both"


class ComplianceRole(str, Enum):
    CLIENT = "client"
    SERVER = "server"
    COLLECTOR = "collector"
    EXPORTER = "exporter"
    INSTRUMENTATION = "instrumentation"


class ComplianceLevel(str, Enum):
    CLAIMS = "claims"
    TESTED = "tested"
    CERTIFIED = "certified"


# ============================================================
# Node Models
# ============================================================

class Principle(BaseModel):
    """Agent의 핵심 능력/책임 (불변)"""
    id: str = Field(..., pattern=r"^p:[a-z-]+$")
    name: str
    description: str
    facets: list[str] = Field(default_factory=list)


class Standard(BaseModel):
    """프로토콜, 규약, 스키마 등 상호운용성 표준"""
    id: str = Field(..., pattern=r"^std:[a-z0-9-]+$")
    name: str
    aliases: list[str] = Field(default_factory=list)
    
    standard_type: StandardType
    steward: str
    governance: GovernanceType
    status: StatusType
    versioning_scheme: VersioningScheme
    
    first_published: Optional[date] = None
    tags: list[str] = Field(default_factory=list)


class StandardVersion(BaseModel):
    """Standard의 특정 버전"""
    id: str = Field(..., pattern=r"^stdv:[a-z0-9-]+@.+$")
    standard: str  # Standard ID
    version: str
    
    status: StatusType
    published_at: Optional[date] = None
    spec_source: Optional[str] = None  # Document ID
    changelog_source: Optional[str] = None  # Document ID
    tags: list[str] = Field(default_factory=list)


class Method(BaseModel):
    """연구 기법, 패턴, 알고리즘"""
    id: str = Field(..., pattern=r"^m:[a-z0-9-]+$")
    name: str
    aliases: list[str] = Field(default_factory=list)
    
    method_family: MethodFamily
    method_type: MethodType
    granularity: Granularity
    method_kind: list[str] = Field(default_factory=list)
    
    description: str
    year_introduced: Optional[int] = None
    maturity: Maturity = Maturity.RESEARCH
    
    seminal_source: Optional[str] = None  # Document ID
    key_sources: list[str] = Field(default_factory=list)  # Document IDs
    tags: list[str] = Field(default_factory=list)


class Implementation(BaseModel):
    """프레임워크, SDK, 라이브러리, 서비스 등 실제 구현체"""
    id: str = Field(..., pattern=r"^impl:[a-z0-9-]+$")
    name: str
    aliases: list[str] = Field(default_factory=list)
    
    impl_type: ImplType
    distribution: Distribution
    
    maintainer: str
    license: Optional[str] = None
    source_repo: Optional[str] = None
    docs: list[str] = Field(default_factory=list)  # Document IDs
    
    languages: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    
    status: StatusType = StatusType.STABLE
    tags: list[str] = Field(default_factory=list)


class Release(BaseModel):
    """Implementation의 특정 버전"""
    id: str = Field(..., pattern=r"^rel:[a-z0-9-]+@.+$")
    implementation: str  # Implementation ID
    version: str
    
    released_at: Optional[date] = None
    status: StatusType = StatusType.STABLE
    
    changelog_source: Optional[str] = None  # Document ID
    security_advisories: list[str] = Field(default_factory=list)  # CVE IDs


class Document(BaseModel):
    """논문, 스펙, 문서 등 지식의 출처"""
    id: str = Field(..., pattern=r"^doc:[a-z0-9-]+$")
    title: str
    
    doc_type: DocType
    authors: list[str] = Field(default_factory=list)
    venue: Optional[str] = None
    year: Optional[int] = None
    
    url: Optional[str] = None
    doi: Optional[str] = None
    
    abstract: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    """문서의 특정 구간"""
    id: str = Field(..., pattern=r"^chunk:[a-z0-9-:]+$")
    document: str  # Document ID
    
    section: Optional[str] = None
    page: Optional[int] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    
    content: str
    content_hash: str
    
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    # embedding_vector는 별도 처리 (vector store)


class Claim(BaseModel):
    """관계의 근거를 reify한 노드"""
    id: str = Field(..., pattern=r"^claim:[a-z0-9-]+$")
    
    predicate: str
    subject: str  # Node ID
    object: str  # Node ID
    
    stance: Stance = Stance.SUPPORTS
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    observed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    extractor_id: Optional[str] = None
    
    supported_by_chunks: list[str] = Field(default_factory=list)  # DocumentChunk IDs
    supported_by_docs: list[str] = Field(default_factory=list)  # Document IDs


# ============================================================
# Relationship Models
# ============================================================

class AddressesRelation(BaseModel):
    """Method → Principle 관계"""
    role: AddressRole
    weight: float = Field(ge=0.0, le=1.0, default=1.0)


class ImplementsRelation(BaseModel):
    """Implementation → Method 관계"""
    support_level: SupportLevel
    evidence: EvidenceType = EvidenceType.DOC


class CompliesWithRelation(BaseModel):
    """Implementation → StandardVersion 관계"""
    role: ComplianceRole
    level: ComplianceLevel = ComplianceLevel.CLAIMS


# ============================================================
# Query/Response Models
# ============================================================

class NodeSearchResult(BaseModel):
    """노드 검색 결과"""
    id: str
    name: str
    node_type: str
    score: float = 1.0
    highlights: list[str] = Field(default_factory=list)


class PathResult(BaseModel):
    """경로 검색 결과"""
    principle: str
    method: str
    implementations: list[str]
    relationships: list[dict]
