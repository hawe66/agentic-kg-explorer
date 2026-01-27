# Agentic AI Knowledge Graph - Schema Definition

> Version: 1.0.0
> Last Updated: 2026-01-27
> Status: Final (Phase 1 Ready)

---

## Overview

이 문서는 Agentic AI 도메인의 지식 그래프 스키마를 정의합니다.
논문, 프레임워크, 서비스 문서를 통합하여 연구-서비스 간 공진화를 지원합니다.

### Design Principles

1. **Principle 불변**: 11개 Principle은 고정된 상위 개념
2. **레이어 분리**: Principle → Method → Implementation → Standard
3. **관계 명확화**: `implements` 의미 분리 (ADDRESSES vs IMPLEMENTS)
4. **증거 기반**: 모든 관계는 문서 근거(Claim) 필요
5. **버전 관리**: Standard/Implementation은 버전 추적 필수

---

## Node Types

### 1. Principle (불변 - 11개)

Agent의 핵심 능력/책임을 나타내는 최상위 개념. **절대 수정 불가.**

```yaml
Principle:
  id: string              # "p:memory", "p:reasoning"
  name: string
  description: string
  
  # 하위 구조 (Facets)
  facets: [string]        # 세부 능력 목록
```

**확정된 11개 Principle:**

| ID | Name | Description |
|---|---|---|
| p:perception | Perception | 환경으로부터 정보를 수집하고 해석하는 능력 |
| p:memory | Memory | 정보를 저장, 검색, 갱신하여 일관성과 학습을 지원 |
| p:planning | Planning | 목표를 하위 과제로 분해하고 실행 순서를 생성 |
| p:reasoning | Reasoning | 논리적 추론을 통해 결론이나 판단을 도출 |
| p:tool-use | Tool Use & Action | 외부 도구를 선택하고 호출하여 작업 완수 |
| p:reflection | Reflection | 자신의 출력/추론/행동을 평가하고 개선 |
| p:grounding | Grounding | 외부 지식에 기반하여 사실적 출력 생성 |
| p:learning | Learning | 피드백과 경험으로부터 지속적 능력 향상 |
| p:multi-agent | Multi-Agent Collaboration | 여러 Agent 간 협력/조정 메커니즘 |
| p:guardrails | Guardrails | 안전성, 보안, 규정 준수를 위한 제어 |
| p:tracing | Tracing | 실행 흐름과 성능을 관찰하고 분석 |

---

### 2. Standard

프로토콜, 규약, 스키마 등 상호운용성 표준.

```yaml
Standard:
  id: string              # "std:mcp", "std:a2a", "std:otel-genai"
  name: string
  aliases: [string]
  
  standard_type: enum
    - "protocol"
    - "semantic_convention"
    - "schema"
    - "guideline"
  
  steward: string         # Anthropic, Google, CNCF, etc.
  governance: enum
    - "company"
    - "foundation"
    - "community"
  
  status: enum
    - "draft"
    - "experimental"
    - "stable"
    - "deprecated"
  
  versioning_scheme: enum
    - "semver"
    - "date"
    - "other"
  
  first_published: date
  tags: [string]
```

---

### 3. StandardVersion

Standard의 특정 버전. 호환성 추적에 필수.

```yaml
StandardVersion:
  id: string              # "stdv:mcp@2025-03-26"
  standard: Standard_ID
  version: string
  
  status: enum
    - "draft"
    - "experimental"
    - "stable"
    - "deprecated"
  
  published_at: date
  spec_source: Document_ID
  changelog_source: Document_ID
  tags: [string]
```

---

### 4. Method

연구 기법, 패턴, 알고리즘. 논문에서 제안된 개념.

```yaml
Method:
  id: string              # "m:react", "m:cot", "m:graphrag"
  name: string
  aliases: [string]
  
  # 1차 분류 (통제된 vocabulary)
  method_family: enum
    - "prompting_decoding"
    - "agent_loop_pattern"
    - "workflow_orchestration"
    - "retrieval_grounding"
    - "memory_system"
    - "reflection_verification"
    - "multi_agent_coordination"
    - "training_alignment"
    - "safety_control"
    - "evaluation"
    - "observability_tracing"
  
  # 2차 분류 (형태)
  method_type: enum
    - "prompt_pattern"
    - "decoding_strategy"
    - "search_planning_algo"
    - "agent_control_loop"
    - "workflow_pattern"
    - "retrieval_indexing"
    - "memory_architecture"
    - "coordination_pattern"
    - "training_objective"
    - "safety_classifier_or_policy"
    - "evaluation_protocol"
    - "instrumentation_pattern"
  
  # 조합 여부
  granularity: enum
    - "atomic"
    - "composite"
  
  method_kind: [string]   # 자유 태그
  
  description: string
  year_introduced: int
  
  maturity: enum
    - "research"
    - "production"
    - "standardized"
    - "legacy"
  
  seminal_source: Document_ID
  key_sources: [Document_ID]
  tags: [string]
```

---

### 5. Implementation

프레임워크, SDK, 라이브러리, 서비스 등 실제 구현체.

```yaml
Implementation:
  id: string              # "impl:langchain", "impl:langgraph"
  name: string
  aliases: [string]
  
  impl_type: enum
    - "framework"
    - "sdk"
    - "library"
    - "service"
    - "model"
    - "tool"
  
  distribution: enum
    - "oss"
    - "managed"
    - "hosted_model"
    - "internal"
  
  maintainer: string
  license: string
  source_repo: string     # GitHub URL
  docs: [Document_ID]
  
  languages: [string]
  platforms: [string]
  
  status: enum
    - "active"
    - "deprecated"
    - "experimental"
  
  tags: [string]
```

---

### 6. Release

Implementation의 특정 버전. 보안/변경사항 추적.

```yaml
Release:
  id: string              # "rel:langchain@0.3.0"
  implementation: Implementation_ID
  version: string
  
  released_at: date
  
  status: enum
    - "active"
    - "deprecated"
    - "yanked"
  
  changelog_source: Document_ID
  security_advisories: [string]  # CVE IDs
```

---

### 7. Document

논문, 스펙, 문서 등 지식의 출처.

```yaml
Document:
  id: string              # "doc:react-2022"
  title: string
  
  doc_type: enum
    - "paper"
    - "spec"
    - "guide"
    - "blog"
    - "repo"
  
  authors: [string]
  venue: string           # arXiv, ICLR, etc.
  year: int
  
  url: string
  doi: string
  
  abstract: string
  tags: [string]
```

---

### 8. DocumentChunk

문서의 특정 구간. 임베딩 및 증거 연결용.

```yaml
DocumentChunk:
  id: string              # "chunk:react-2022:sec3.2"
  document: Document_ID
  
  # 위치 정보
  section: string
  page: int
  start_offset: int
  end_offset: int
  
  # 내용
  content: string
  content_hash: string    # 중복/변조 감지
  
  # 임베딩
  embedding_model: string
  embedding_dim: int
  embedding_vector: [float]
```

---

### 9. Claim

관계의 근거를 reify한 노드. 증거 기반 KG의 핵심.

```yaml
Claim:
  id: string              # "claim:001"
  
  # 주장 내용
  predicate: string       # "PROPOSES", "IMPLEMENTS", "ADDRESSES"
  subject: Node_ID
  object: Node_ID
  
  # 신뢰도
  stance: enum
    - "supports"
    - "refutes"
    - "mentions"
  confidence: float       # 0.0 ~ 1.0
  
  # 시간 정보
  observed_at: datetime   # 문서가 말하는 시점
  created_at: datetime    # Claim 생성 시점
  
  # 추출 정보
  extractor_id: string    # 추출기 버전
  
  # 근거 연결
  supported_by_chunks: [DocumentChunk_ID]
  supported_by_docs: [Document_ID]
```

---

## Relationships

### Document 관계

```cypher
// 논문이 Method를 제안
(:Document:Paper)-[:PROPOSES]->(:Method)

// 논문이 Method를 평가
(:Document:Paper)-[:EVALUATES]->(:Method)

// 문서가 Implementation을 설명
(:Document)-[:DESCRIBES]->(:Implementation)

// 스펙이 Standard를 정의
(:Document:Spec)-[:SPECIFIES]->(:Standard)
```

### Method 관계

```cypher
// Method가 Principle을 달성/개선
(:Method)-[:ADDRESSES {
  role: "primary" | "secondary",
  weight: float  // 0.0 ~ 1.0
}]->(:Principle)

// Method 확장 (기존 Method를 개선)
(:Method)-[:EXTENDS]->(:Method)

// Method 변형 (같은 아이디어의 다른 버전)
(:Method)-[:VARIANT_OF]->(:Method)

// Method 사용 (composite method용)
(:Method)-[:USES]->(:Method)
```

### Implementation 관계

```cypher
// Implementation이 Method를 구현
(:Implementation)-[:IMPLEMENTS {
  support_level: "core" | "first_class" | "template" | "integration" | "experimental",
  evidence: "doc" | "code" | "both"
}]->(:Method)

// Implementation이 Standard를 준수
(:Implementation)-[:COMPLIES_WITH {
  role: "client" | "server" | "collector" | "exporter" | "instrumentation",
  level: "claims" | "tested" | "certified"
}]->(:StandardVersion)

// Implementation이 다른 Implementation을 계측
(:Implementation)-[:INSTRUMENTS]->(:Implementation)

// Implementation 통합
(:Implementation)-[:INTEGRATES_WITH]->(:Implementation)

// Implementation의 Release
(:Implementation)-[:HAS_RELEASE]->(:Release)
```

### Standard 관계

```cypher
// Standard의 버전
(:Standard)-[:HAS_VERSION]->(:StandardVersion)
```

### Evidence 관계

```cypher
// Chunk가 노드를 언급
(:DocumentChunk)-[:MENTIONS]->(:AnyNode)

// Chunk가 Claim을 뒷받침
(:DocumentChunk)-[:SUPPORTS]->(:Claim)
```

---

## ID Namespace Convention

| Node Type | Prefix | Example |
|---|---|---|
| Principle | `p:` | `p:memory` |
| Method | `m:` | `m:react` |
| Implementation | `impl:` | `impl:langchain` |
| Standard | `std:` | `std:mcp` |
| StandardVersion | `stdv:` | `stdv:mcp@2025-03-26` |
| Release | `rel:` | `rel:langchain@0.3.0` |
| Document | `doc:` | `doc:react-2022` |
| DocumentChunk | `chunk:` | `chunk:react-2022:sec3` |
| Claim | `claim:` | `claim:001` |

---

## Validation Queries

### 1. Paper 없는 Method 찾기

```cypher
MATCH (m:Method)
WHERE NOT (m)<-[:PROPOSES]-(:Document:Paper)
  AND m.seminal_source IS NULL
RETURN m.id, m.name;
```

### 2. Principle에 연결 안 된 Method

```cypher
MATCH (m:Method)
WHERE NOT (m)-[:ADDRESSES]->(:Principle)
RETURN m.id, m.name;
```

### 3. 증거 없는 IMPLEMENTS 관계

```cypher
MATCH (i:Implementation)-[r:IMPLEMENTS]->(m:Method)
WHERE NOT EXISTS {
  MATCH (c:Claim {subject: i.id, object: m.id, predicate: "IMPLEMENTS"})
}
RETURN i.name, m.name;
```

### 4. Standard 준수 관계 없는 Observability 구현체

```cypher
MATCH (i:Implementation)
WHERE i.impl_type IN ["service", "library"]
  AND (i.name CONTAINS "Langfuse" OR i.name CONTAINS "LangSmith")
  AND NOT (i)-[:COMPLIES_WITH]->(:StandardVersion)
RETURN i.name;
```

### 5. Principle → Method → Implementation 전체 경로

```cypher
MATCH path = (p:Principle)<-[:ADDRESSES]-(m:Method)<-[:IMPLEMENTS]-(i:Implementation)
RETURN p.name, m.name, collect(i.name) AS implementations
ORDER BY p.name;
```

---

## Appendix: Principle 하위 구조 (Facets)

### Perception
- Input Modalities: Text, Vision, Audio, Structured Data
- Observation Sources: Environment State, Tool Output, User Input, UI/GUI State
- Input Processing: Parsing, Normalization, Context Extraction

### Memory
- Memory Types (By Duration): Short-term, Long-term
- Memory Types (By Content): Episodic, Semantic, Procedural
- Memory Operations: Storage, Retrieval, Update, Consolidation, Forgetting
- Memory Architecture: Context Window Management, Memory Hierarchy, Memory Indexing

### Planning
- Execution Paradigm: Workflow, Agent
- Task Decomposition: Upfront, Interleaved
- Orchestration Patterns: Sequential, Conditional, Parallel, Hierarchical
- Human-in-the-Loop: Approval Gates, Intervention Points, Escalation
- Plan Adaptation: Replanning, Error Recovery

### Reasoning
- Reasoning Types: Deductive, Inductive, Abductive, Analogical
- Reasoning Domains: Mathematical, Commonsense, Causal, Temporal, Spatial
- Reasoning Enhancement: Step-by-step Elicitation, Multi-path Exploration, Self-consistency, External Knowledge
- Reasoning Verification: Self-check, Cross-validation, Formal Verification

### Tool Use & Action
- Tool Lifecycle: Discovery, Selection, Invocation, Output Processing
- Integration Patterns: Direct API, Plugin, Protocol-based, Code Execution
- Tool Categories: Information Retrieval, Computation, External Services, System Interaction, Physical Actuation
- Execution Patterns: Sequential, Parallel, Iterative, Nested

### Reflection
- Reflection Process: Self-Evaluation, Feedback Generation, Refinement
- Feedback Sources: Intrinsic, Extrinsic (Tool/Environment/Model/Human)
- Reflection Scope: Output-level, Reasoning-level, Action-level, Strategy-level
- Reflection Timing: Immediate, Post-hoc, Episodic

### Grounding
- Grounding Types: Factual, Contextual, Temporal
- Knowledge Source Types: Unstructured, Semi-structured, Structured, Real-time
- Grounding Approaches: Retrieval-based, KG-based, Fine-tuning-based, Constraint-based

### Learning
- Learning Mechanisms: Non-parametric (In-context, Memory-augmented), Parametric (Supervised, Reinforcement)
- Learning Sources: Demonstration, Feedback, Experience
- Learning Scope: Task-specific, Cross-task, Continual/Lifelong

### Multi-Agent Collaboration
- Collaboration Types: Cooperation, Competition, Coopetition
- Topology: Centralized, Decentralized, Hierarchical, Dynamic
- Coordination Strategies: Role-based, Rule-based, Negotiation-based
- Communication: Message Passing, Shared State, Broadcast

### Guardrails
- Threat Types: Prompt Injection, Data Exfiltration, Unauthorized Action, Output Manipulation
- Attack Surfaces: User Input, Retrieved Content, Tool I/O, Inter-agent Communication
- Protected Assets: System Instructions, Credentials, User Data, External Resources
- Control Mechanisms: Input Validation, Output Filtering, Sandboxing, Access Control, Human Approval
- Compliance: Policy Enforcement, Regulatory Alignment, Audit Logging

### Tracing
- Trace Schema: Span Types, Trace Structure, Event Types
- Captured Metadata: Inputs/Outputs, Timing, Resource Usage, Versioning
- Evaluation Framework: Offline, Online, Automated, Human Review
- Quality Metrics: Correctness, Relevance, Groundedness, Safety
- Operational Metrics: Latency, Throughput, Error Rate, Cost
