# Claude Code Project Context

> 이 파일은 Claude Code가 프로젝트를 이해하는 데 필요한 핵심 컨텍스트입니다.
> Claude Code 시작 시 자동으로 읽힙니다.

---

## 프로젝트 개요

**Agentic AI Knowledge Graph** - Agentic AI 도메인의 연구(논문)와 서비스(프레임워크/라이브러리) 간 공진화를 추적하는 지식 그래프 시스템.

### 핵심 목표
1. 논문에서 제안된 Method가 어떤 Implementation에서 구현되는지 추적
2. Implementation이 어떤 Standard를 준수하는지 추적
3. 모든 관계에 문서 근거(Claim) 연결

---

## 레이어 구조 (불변)

```
Principle (11개 고정)
    ↑ ADDRESSES {role, weight}
  Method (연구 기법)
    ↑ IMPLEMENTS {support_level, evidence}
Implementation (프레임워크/서비스)
    ↑ COMPLIES_WITH {role, level}
StandardVersion (표준 버전)
    ↑ HAS_VERSION
  Standard (표준)
```

---

## 11 Principles (절대 수정 불가)

| ID | Name | Description |
|---|---|---|
| p:perception | Perception | 환경으로부터 정보를 수집하고 해석 |
| p:memory | Memory | 정보 저장, 검색, 갱신 |
| p:planning | Planning | 목표를 하위 과제로 분해, 실행 순서 생성 |
| p:reasoning | Reasoning | 논리적 추론으로 결론/판단 도출 |
| p:tool-use | Tool Use & Action | 외부 도구 선택 및 호출 |
| p:reflection | Reflection | 자기 평가 및 개선 |
| p:grounding | Grounding | 외부 지식 기반 사실적 출력 |
| p:learning | Learning | 피드백/경험 기반 능력 향상 |
| p:multi-agent | Multi-Agent Collaboration | 에이전트 간 협력/조정 |
| p:guardrails | Guardrails | 안전성, 보안, 규정 준수 |
| p:tracing | Tracing | 실행 흐름 관찰 및 분석 |

---

## 핵심 설계 결정 (Design Decisions)

### 1. Standard 버전 분리
- `Standard` + `StandardVersion` 노드 분리
- 이유: MCP(날짜 기반), A2A(semver), OTel(experimental 상태) 등 다양한 버전 정책

### 2. Method 분류 체계
```yaml
method_family: 1차 분류 (통제된 vocabulary)
  - prompting_decoding
  - agent_loop_pattern
  - workflow_orchestration
  - retrieval_grounding
  - memory_system
  - reflection_verification
  - multi_agent_coordination
  - training_alignment
  - safety_control
  - evaluation
  - observability_tracing

method_type: 2차 분류 (형태)
  - prompt_pattern
  - decoding_strategy
  - search_planning_algo
  - agent_control_loop
  - workflow_pattern
  - retrieval_indexing
  - memory_architecture
  - coordination_pattern
  - training_objective
  - safety_classifier_or_policy
  - evaluation_protocol
  - instrumentation_pattern

granularity: atomic | composite
```

### 3. 관계 의미 구분
- `ADDRESSES`: Method → Principle (Method가 Principle을 "달성/개선")
- `IMPLEMENTS`: Implementation → Method (support_level로 구현 수준 표시)
- `COMPLIES_WITH`: Implementation → StandardVersion (role, level로 준수 수준 표시)
- `USES`: Method → Method (composite method가 atomic method 사용)

### 4. support_level 정의
| Level | 의미 |
|-------|------|
| core | 프레임워크의 핵심 기능 |
| first_class | 공식 지원, 문서화됨 |
| template | 템플릿/예제로 제공 |
| integration | 서드파티 통합 |
| experimental | 실험적 지원 |

### 5. Claim 기반 증거 추적
- 모든 관계는 `Claim` 노드로 근거 추적 가능
- `stance`: supports | refutes | mentions
- `observed_at`: 문서가 말하는 시점
- `extractor_id`: 추출기 버전 (재현성)

---

## ID 네이밍 규칙

| Node Type | Prefix | Example |
|---|---|---|
| Principle | `p:` | `p:memory` |
| Method | `m:` | `m:react` |
| Implementation | `impl:` | `impl:langchain` |
| Standard | `std:` | `std:mcp` |
| StandardVersion | `stdv:` | `stdv:mcp@2025-03-26` |
| Release | `rel:` | `rel:langchain@0.3.0` |
| Document | `doc:` | `doc:react-2022` |
| Claim | `claim:` | `claim:001` |

---

## 파일 구조

```
agentic-ai-kg/
├── CLAUDE.md              ← 이 파일 (컨텍스트)
├── docs/
│   └── schema.md          ← 전체 스키마 정의서
├── neo4j/
│   ├── schema.cypher      ← 제약조건/인덱스
│   ├── seed_data.cypher   ← 초기 데이터 (11 Principles, 25+ Methods, 15+ Implementations)
│   └── validation_queries.cypher ← 검증 쿼리
├── src/
│   ├── db_setup.py        ← DB 초기화
│   └── models.py          ← Pydantic 모델
├── requirements.txt
└── .env.example
```

---

## 개발 로드맵

### Phase 1: 기반 구축 ✅ (현재)
- [x] 스키마 설계
- [x] Neo4j 세팅 스크립트
- [x] Seed 데이터
- [ ] 수동 데이터 검증

### Phase 2: 핵심 플로우
- [ ] LangGraph 기본 구조
- [ ] 벡터 검색 연동
- [ ] FastAPI + Streamlit

### Phase 3: 확장 기능
- [ ] Web Search Expander
- [ ] 유저 승인 UI
- [ ] 그래프 시각화

### Phase 4: Critic Agent
- [ ] 평가 원칙/방법 정의
- [ ] 평가 로직 구현

### Phase 5: Prompt Optimizer
- [ ] Failure Analyzer
- [ ] Variant Generator

---

## 주요 관계 예시

```cypher
// Method가 Principle을 달성
(m:Method {id: 'm:react'})-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p:Principle {id: 'p:tool-use'})
(m:Method {id: 'm:react'})-[:ADDRESSES {role: 'secondary', weight: 0.7}]->(p:Principle {id: 'p:reasoning'})

// Implementation이 Method를 구현
(i:Implementation {id: 'impl:langchain'})-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m:Method {id: 'm:react'})

// Composite Method가 Atomic Method 사용
(m:Method {id: 'm:cot-sc'})-[:USES]->(m:Method {id: 'm:cot'})
(m:Method {id: 'm:cot-sc'})-[:USES]->(m:Method {id: 'm:self-consistency'})

// Implementation이 Standard 준수
(i:Implementation {id: 'impl:langfuse'})-[:COMPLIES_WITH {role: 'collector', level: 'claims'}]->(sv:StandardVersion {id: 'stdv:otel-genai@1.30'})
```

---

## 경계 규칙 (중요)

1. **Orchestration vs Multi-Agent**
   - Orchestration: 관리자 관점 (top-down), Planning Principle
   - Multi-Agent: 상호작용 메커니즘 (horizontal), Multi-Agent Principle

2. **Guardrails vs Alignment**
   - Guardrails: Inference-time 제어
   - Alignment (Learning): Training-time 학습

3. **Reflection vs Tracing**
   - Reflection: Agent가 자기 평가 (내부)
   - Tracing: 외부 시스템이 관찰 (외부)

4. **Memory vs Grounding**
   - Memory: 내부 상태 저장/검색
   - Grounding: 외부 지식 기반 검증

---

## 작업 시 참고사항

1. **스키마 변경 시**: `docs/schema.md` 먼저 업데이트
2. **새 Method 추가 시**: 반드시 `ADDRESSES` 관계로 Principle 연결
3. **새 Implementation 추가 시**: 반드시 `IMPLEMENTS` 관계로 Method 연결
4. **Principle 추가/수정 금지**: 11개는 불변

---

## 자주 쓰는 Cypher 쿼리

```cypher
// Principle → Method → Implementation 전체 경로
MATCH path = (p:Principle)<-[:ADDRESSES]-(m:Method)<-[:IMPLEMENTS]-(i:Implementation)
RETURN p.name, m.name, collect(i.name) AS implementations
ORDER BY p.name;

// 특정 Method를 구현하는 Implementation
MATCH (i:Implementation)-[r:IMPLEMENTS]->(m:Method {id: 'm:react'})
RETURN i.name, r.support_level, r.evidence;

// Paper 없는 Method (데이터 품질 체크)
MATCH (m:Method)
WHERE NOT (m)<-[:PROPOSES]-(:Document:Paper)
  AND m.seminal_source IS NULL
RETURN m.id, m.name;
```
