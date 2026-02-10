# Claude Code Project Context

> 이 파일은 Claude Code가 프로젝트를 이해하는 데 필요한 핵심 컨텍스트입니다.
> Claude Code 시작 시 자동으로 읽힙니다.

---

## 프로젝트 비전

### 개요: "Agentic AI 지식 그래프 탐색기"

개인이 수집한 Agentic AI 관련 논문/아티클/메모를 하나의 그래프로 구조화하고, 대화형 에이전트가 탐색·요약·확장을 도와주는 시스템. 없는 정보는 웹에서 찾아 추천하고, **Critic Agent**가 전체 품질을 관리한다.

### 핵심 동기

#### 1. 지식그래프 기반 지식 확장
- 쏟아지는 새로운 정보를 단순 요약/추천으로는 **내 지식체계에 맞게 확장할 수 없음**
- 기존 지식을 그래프화하고, **관계성을 고려**해 새로운 지식을 추천/추가
- Agentic AI 도메인을 PoC 대상으로 선정

#### 2. 가치함수 학습 이론 기반 프롬프트 자동화
- **강화학습 인사이트**: Action Space가 넓을 경우, 가치함수(V)를 먼저 학습한 뒤 행동-가치함수(Q)를 학습하는 것이 안정적
- **적용 아이디어**: 원칙(V) → 평가기준 → 행동(Q, 프롬프트)
  - ISO 표준 정의에서도 원칙을 우선 설정하고 평가 기준을 다음으로 제작함
  - Critic Agent와 원칙에 대해 토론하고, 평가 기준을 만들어 각 Agent 프롬프트를 평가/고도화

### 핵심 목표
1. 논문에서 제안된 Method가 어떤 Implementation에서 구현되는지 추적
2. Implementation이 어떤 Standard를 준수하는지 추적
3. 모든 관계에 문서 근거(Claim) 연결
4. **Critic Agent가 원칙 기반 평가로 프롬프트 자동 최적화**

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
| EvaluationCriteria | `ec:` | `ec:reasoning-completeness` |
| Evaluation | `eval:` | `eval:001` |
| FailurePattern | `fp:` | `fp:incomplete-reasoning` |
| PromptVersion | `pv:` | `pv:synthesizer@2.1.0` |

---

## 파일 구조

```
agentic-ai-kg/
├── CLAUDE.md              ← 이 파일 (컨텍스트)
├── config/                ← 설정 파일 (✅ P1, Phase 4, Phase 5)
│   ├── intents.yaml       ← 11개 intent 정의 + examples
│   ├── cypher_templates.yaml ← 20+ Cypher 템플릿 (intent별)
│   ├── providers.yaml     ← LLM/Embedding provider 설정
│   ├── evaluation_criteria.yaml ← 15개 평가 기준 (Phase 4)
│   └── test_queries.yaml  ← 프롬프트 최적화용 테스트 쿼리 (Phase 5)
├── data/
│   ├── entity_catalog.json ← KG 엔티티 목록 (generated)
│   └── embedding_hashes.json ← 임베딩 변경 추적
├── docs/
│   ├── schema.md          ← 전체 스키마 정의서
│   ├── phase4-critic-agent-design.md ← Critic Agent 설계 문서
│   └── phase5-prompt-optimizer-design.md ← Prompt Optimizer 설계 문서
├── neo4j/
│   ├── schema.cypher      ← 제약조건/인덱스 (Phase 4 schema 포함)
│   ├── seed_data.cypher   ← 초기 데이터 (11 Principles, 33 Methods, 16 Implementations)
│   ├── seed_evaluation.cypher ← 평가 기준 seed 데이터 (Phase 4)
│   └── validation_queries.cypher ← 검증 쿼리
├── src/
│   ├── graph/             ← Neo4j 클라이언트 & 스키마
│   ├── agents/            ← LangGraph 에이전트 파이프라인 (✅ 구현)
│   │   ├── state.py       ← AgentState (intent: str로 변경, 동적 지원)
│   │   ├── graph.py       ← LangGraph 파이프라인 (conditional 5-node + evaluate hook)
│   │   ├── providers/     ← LLM provider 추상화
│   │   └── nodes/
│   │       ├── intent_classifier.py  ← YAML 기반 의도 분류 (11 intents)
│   │       ├── search_planner.py     ← YAML 기반 Cypher 선택 (20+ templates)
│   │       ├── graph_retriever.py    ← Neo4j + ChromaDB 쿼리
│   │       ├── web_search.py         ← Tavily 웹 검색
│   │       └── synthesizer.py        ← 다차원 confidence 답변 생성
│   ├── critic/            ← Critic Agent 모듈 (✅ Phase 4)
│   │   ├── criteria.py    ← YAML에서 평가 기준 로드
│   │   ├── scorer.py      ← LLM 기반 점수 산정
│   │   └── evaluator.py   ← CriticEvaluator 오케스트레이션
│   ├── ingestion/         ← 문서 수집 모듈 (✅ P2)
│   │   ├── crawler.py     ← URL/PDF 텍스트 추출
│   │   ├── chunker.py     ← 문서 청킹
│   │   └── linker.py      ← Document → KG 관계 추출
│   ├── optimizer/         ← Prompt Optimizer 모듈 (✅ Phase 5)
│   │   ├── models.py      ← FailurePattern, PromptVariant, PromptVersion
│   │   ├── analyzer.py    ← 실패 패턴 탐지 + LLM 가설 생성
│   │   ├── generator.py   ← 프롬프트 변형 생성
│   │   ├── runner.py      ← 테스트 실행 + 평가
│   │   └── registry.py    ← 프롬프트 버전 관리
│   ├── retrieval/         ← 벡터 검색 모듈
│   │   ├── providers/     ← Embedding provider 추상화
│   │   └── vector_store.py ← ChromaDB wrapper
│   ├── api/               ← FastAPI 엔드포인트 (/evaluations, /evaluation-criteria, /optimizer/* 포함)
│   └── ui/                ← Streamlit Chat UI (evaluation, document upload, optimizer Gate 1/2, version history)
├── scripts/
│   ├── generate_entity_catalog.py ← KG → entity_catalog.json 생성
│   ├── generate_embeddings.py     ← KG 노드 임베딩 → ChromaDB
│   ├── test_agent.py              ← 에이전트 CLI 테스트
│   ├── seed_evaluation_criteria.py ← EvaluationCriteria → Neo4j
│   ├── ingest_document.py         ← 문서 수집 CLI (URL/PDF)
│   ├── analyze_failures.py        ← 실패 패턴 분석 CLI (Phase 5)
│   └── run_optimization.py        ← 프롬프트 최적화 파이프라인 CLI (Phase 5)
├── pyproject.toml
└── .env.example
```

---

## 개발 로드맵

### Phase 1: 기반 구축 ✅ 완료
- [x] 스키마 설계
- [x] Neo4j 세팅 스크립트
- [x] Seed 데이터
- [x] 수동 데이터 검증

### Phase 2: 핵심 플로우 ✅ 완료
- [x] LangGraph 기본 구조 (4-node linear pipeline)
- [x] 에이전트 테스트 스크립트 (`scripts/test_agent.py`)
- [x] LLM provider/model 추상화 (OpenAI, Anthropic, Gemini 지원)
- [x] SSL 조건부 처리 (macOS/Windows/WSL 호환)
- [x] Provider config 외부화 (`config/providers.yaml`)
- [x] 벡터 검색 연동 (ChromaDB + OpenAI embeddings)
- [x] FastAPI REST endpoints (POST /query, GET /health, /stats, /graph/principles)
- [x] Streamlit Chat UI

### Phase 3: 확장 기능 ✅ 완료
- [x] Web Search Expander (Tavily API, conditional pipeline)
- [x] 유저 승인 UI (웹 결과 → KG 추가)
- [x] 그래프 시각화 (streamlit-agraph, toggle/legend/node colors)

### P0/P1 Fixes ✅ 완료
- [x] Confidence 계산 재설계 (4-dimension weighted)
- [x] `out_of_scope` intent + Entity Catalog
- [x] Intent 분류 체계 확장 (`config/intents.yaml`, 11 intents)
- [x] Cypher 템플릿 외부화 (`config/cypher_templates.yaml`, 20+ templates)
- [x] Streamlit UI 개선 (example auto-execute, floating panels)

### Phase 4: Critic Agent ✅ 완료
- [x] 평가 기준 정의 (`config/evaluation_criteria.yaml`, 15개 기준)
- [x] 평가 로직 구현 (`src/critic/` 모듈)
- [x] Neo4j 스키마 확장 (EvaluationCriteria, Evaluation, FailurePattern, PromptVersion)
- [x] API 엔드포인트 (`GET /evaluations`, `GET /evaluation-criteria`)
- [x] Streamlit UI 통합 (평가 점수 표시)

### P2: Document Pipeline ✅ 완료
- [x] 범용 문서 크롤러 (`src/ingestion/crawler.py`)
- [x] Local docs 업로드 UI (Streamlit PDF/URL)
- [x] Document → KG 자동 연결 (`src/ingestion/linker.py`)

### Phase 5: Prompt Optimizer ✅ 완료
- [x] Failure Analyzer (`src/optimizer/analyzer.py`)
- [x] Variant Generator (`src/optimizer/generator.py`)
- [x] Test Runner + Critic 연동 (`src/optimizer/runner.py`)
- [x] Prompt Registry (`src/optimizer/registry.py`)
- [x] CLI 도구 (`scripts/analyze_failures.py`, `scripts/run_optimization.py`)
- [x] Streamlit UI 통합 (Human-in-the-Loop): Gate 1/2, Version History, Sidebar
- [x] API 엔드포인트 7개 (`/optimizer/*`) + Pydantic schemas

---

## Critic Agent 시스템 (Phase 4-5 상세)

### 핵심 원칙: V → Q 학습 순서

```
┌─────────────────────────────────────────────────────────┐
│  Principle (가치함수 V)                                 │
│  "무엇이 좋은 Agent 행동인가?"                          │
│                                                         │
│  예: p:reasoning - "논리적 추론으로 결론 도출"          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ 도출
┌─────────────────────────────────────────────────────────┐
│  EvaluationCriteria (평가 기준)                         │
│  "어떻게 측정할 것인가?"                                │
│                                                         │
│  예: "추론 단계가 명시적으로 나열되어야 함"             │
│      "각 단계가 논리적으로 연결되어야 함"               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ 적용
┌─────────────────────────────────────────────────────────┐
│  Prompt (행동-가치함수 Q)                               │
│  "구체적으로 무엇을 지시할 것인가?"                     │
│                                                         │
│  예: "답변 전 반드시 '추론 과정:' 섹션을 포함하세요"    │
└─────────────────────────────────────────────────────────┘
```

### 평가 체계 구조

```
Principle (KG 노드)
    │
    ▼ DERIVED_FROM
EvaluationCriteria (평가 기준)
    │
    ▼ USES_CRITERIA
Evaluation (개별 평가 결과)
    │
    ▼ 축적/분석
FailurePattern (반복 실패 패턴)
    │
    ▼ ADDRESSES
PromptVersion (새 프롬프트)
```

### 그래프 스키마 확장 (Critic/Optimizer 전용)

```yaml
# 평가 기준 (Principle에서 도출)
EvaluationCriteria:
  id: string              # "ec:reasoning-cot-completeness"
  name: string
  description: string
  principle: Principle_ID
  agent_target: string    # 적용 대상 Agent
  scoring_rubric: string
  version: string
  is_active: boolean

# 개별 평가 결과
Evaluation:
  id: string              # "eval:001"
  agent_name: string
  prompt_version: string
  criteria_ids: [string]
  scores: {criteria_id: score}
  feedback: string
  created_at: datetime
  conversation_id: string

# 실패 패턴
FailurePattern:
  id: string              # "fp:reasoning-incomplete-steps"
  pattern_type: string    # "output_quality" | "reasoning" | "tool_use"
  description: string
  frequency: int
  affected_agents: [string]
  root_cause_hypotheses: [string]
  suggested_fixes: [string]

# 프롬프트 버전
PromptVersion:
  id: string              # "pv:synthesizer@2.1.0"
  agent_name: string
  version: string
  content_path: string    # 실제 프롬프트 파일 경로
  is_active: boolean
  user_approved: boolean
  parent_version: string
  performance_delta: float
```

### 전체 최적화 루프

```
┌─────────────────────────────────────┐
│         RUNTIME EXECUTION           │
│   User Query → Agent Pipeline →     │
│   Final Response                    │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│         CRITIC EVALUATION           │
│   - 각 에이전트 평가                │
│   - 평가 결과 저장                  │
└─────────────────────────────────────┘
                    │
               축적 (N회 이상)
                    ▼
┌─────────────────────────────────────┐
│         PATTERN ANALYSIS            │
│   - 반복 실패 패턴 탐지             │
│   - 개선 필요 에이전트 식별         │
└─────────────────────────────────────┘
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
┌──────────────────┐    ┌──────────────────┐
│ GUIDELINE UPDATE │    │ PROMPT OPTIMIZE  │
│ 원칙/방법 수준   │    │ 프롬프트 수준    │
│ 구조적 변경      │    │ 표현/예시 개선   │
└──────────────────┘    └──────────────────┘
      │                           │
      └─────────────┬─────────────┘
                    ▼
┌─────────────────────────────────────┐
│      USER REVIEW & APPROVAL         │
│   - Diff 표시 / 테스트 결과 표시    │
│   - 승인/거절/수정요청              │
└─────────────────────────────────────┘
                    │
                 승인 시
                    ▼
┌─────────────────────────────────────┐
│         VERSION COMMIT              │
│   - 새 버전 생성 / 활성화           │
└─────────────────────────────────────┘
```

### Human-in-the-Loop 이중 게이트

```
실패 패턴 감지
      │
      ▼
┌─────────────────────────────────────┐
│  GATE 1: 가설 승인                  │
│  Critic이 생성한 root_cause_hypotheses│
│  → 유저가 검토/수정/추가            │
└─────────────────────────────────────┘
      │
      ▼
가설 기반 프롬프트 변형 생성 (3개)
      │
      ▼
자동 테스트 실행
      │
      ▼
┌─────────────────────────────────────┐
│  GATE 2: 최종 프롬프트 승인         │
│  변형 중 최고 성능 프롬프트         │
│  → 유저가 검토/수정/거절            │
└─────────────────────────────────────┘
      │
      ▼
Prompt Registry에 새 버전 커밋
```

### 이론적 기반 및 참조 연구

| 연구 | 핵심 아이디어 | 우리의 적용 |
|------|--------------|------------|
| **Self-Refine** [Madaan 2023] | Generate-Feedback-Refine 루프 | 에이전트 프롬프트 반복 개선 |
| **Reflexion** [Shinn 2023] | Verbal Reinforcement | 평가 지침 진화에 언어적 강화학습 |
| **APO** [Pryzant 2023] | 텍스트 그래디언트 | 실패 기반 자연어 개선 방향 생성 |
| **PromptWizard** [Agarwal 2024] | Instruction-Example 공동 최적화 | 지시문+예시 함께 최적화 |

### 차별화 요소
1. **Human-in-the-Loop 이중 승인 게이트**: 가설 승인 → 최종 프롬프트 승인
2. **Critic Agent 분리 및 평가 체계 버저닝**: 평가 기준 자체도 버전 관리
3. **멀티-에이전트 파이프라인 맥락**: 단일 LLM이 아닌 Agent 파이프라인 전체 최적화
4. **KG 기반 원칙 도출**: Principle 노드에서 평가 기준을 체계적으로 도출

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

---

# Project Context

## 환경 설정 (멀티 플랫폼)

### macOS (현재 주 개발 환경)
- Python: pyenv 관리, 3.11.4
- Poetry 가상환경 경로: `~/Library/Caches/pypoetry/virtualenvs/agentic-kg-explorer-I8TSMQ2W-py3.11`
- 실행: `poetry run python ...`
- SSL: 별도 인증서 설정 불필요 (시스템 인증서 사용)

### Windows
- PowerShell 프로필: `C:\Users\조영하\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
- 가상환경 활성화: `kg` 명령어 사용
- Poetry 가상환경 경로: `C:\Users\조영하\AppData\Local\pypoetry\Cache\virtualenvs\agentic-kg-explorer-Vxs5hbQW-py3.11`
- 실행: 위 캐시 폴더의 python 직접 사용 (`poetry run` 불필요)

### WSL
- 프로젝트 폴더 내 `.venv/` 사용
- 실행: `poetry run python ...` 또는 `.venv/bin/activate`

### 공통 주의사항
- 반드시 현재 환경(macOS/Windows/WSL)을 먼저 파악하고 명령어를 실행할 것
- Poetry 환경 밖 global에서는 Python 버전이 다를 수 있음

## SSL 인증서 설정
- Windows: `C:\certs\` — `NODE_EXTRA_CA_CERTS`, `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE` 환경변수 설정
- WSL: `~/certs/` — 별도 설정 필요
- macOS: 불필요 (시스템 기본 인증서 사용, `SSL_CERT_FILE` 미설정 시 provider가 자동으로 기본값 사용)
