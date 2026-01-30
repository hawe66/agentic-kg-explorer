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
├── docs/
│   └── schema.md          ← 전체 스키마 정의서
├── neo4j/
│   ├── schema.cypher      ← 제약조건/인덱스
│   ├── seed_data.cypher   ← 초기 데이터 (11 Principles, 25+ Methods, 15+ Implementations)
│   └── validation_queries.cypher ← 검증 쿼리
├── src/
│   ├── graph/             ← Neo4j 클라이언트 & 스키마
│   ├── agents/            ← LangGraph 에이전트 파이프라인 (✅ 기본 구현)
│   │   ├── __init__.py    ← 모듈 exports
│   │   ├── state.py       ← AgentState TypedDict (11 fields)
│   │   ├── graph.py       ← LangGraph 파이프라인 (linear 4-node)
│   │   ├── README.md      ← 에이전트 아키텍처 문서
│   │   └── nodes/
│   │       ├── intent_classifier.py  ← 쿼리 의도 분류
│   │       ├── search_planner.py     ← Cypher 템플릿 선택 (7개)
│   │       ├── graph_retriever.py    ← Neo4j 쿼리 실행
│   │       └── synthesizer.py        ← 자연어 답변 생성
│   └── api/               ← FastAPI 엔드포인트
├── scripts/
│   ├── load_sample_data.py
│   ├── test_queries.py
│   └── test_agent.py     ← 에이전트 CLI 테스트 (11 test queries)
├── requirements.txt
└── .env.example
```

---

## 개발 로드맵

### Phase 1: 기반 구축 ✅ 완료
- [x] 스키마 설계
- [x] Neo4j 세팅 스크립트
- [x] Seed 데이터
- [x] 수동 데이터 검증

### Phase 2: 핵심 플로우 🔧 진행 중
- [x] LangGraph 기본 구조 (4-node linear pipeline)
- [x] 에이전트 테스트 스크립트 (`scripts/test_agent.py`)
- [ ] LLM 의존성 개선 (provider/model 추상화, SSL 조건부 처리)
- [ ] 벡터 검색 연동
- [ ] FastAPI + Streamlit

### Phase 3: 확장 기능
- [ ] Web Search Expander
- [ ] 유저 승인 UI
- [ ] 그래프 시각화

### Phase 4: Critic Agent
- [ ] 평가 기준 정의 (EvaluationCriteria)
- [ ] 평가 로직 구현 (Evaluation)
- [ ] 지침 버저닝 시스템

### Phase 5: Prompt Optimizer
- [ ] Failure Analyzer (FailurePattern)
- [ ] Variant Generator
- [ ] Test Runner + Critic 연동
- [ ] Prompt Registry (PromptVersion)
- [ ] 최적화 리뷰 UI (Human-in-the-Loop)

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

## 환경 설정
- Windows PowerShell 프로필: `C:\Users\조영하\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
- 가상환경 활성화: `kg` 명령어 사용
- Poetry 가상환경 경로: `C:\Users\조영하\AppData\Local\pypoetry\Cache\virtualenvs\agentic-kg-explorer-Vxs5hbQW-py3.11`
- 주의할 점:
    - 현재 환경이 Windows일 경우 poetry run 등의 명령어를 사용하지 않고, 위의 캐시 폴더에 존재하는 poetry 가상환경 경로를 사용하고, python 명령어를 바로 사용하면 됨.
    - WSL일 경우 프로젝트 폴더에 전용 poetry 환경이 설정된 .venv 폴더가 있으므로 poetry 명령어를 사용해도 됨.
    - 따라서 반드시 현재 환경이 어디인지 파악하고 명령어를 돌려야 함.

## SSL 인증서 설정
- 인증서 위치: `C:\certs\`
- NODE_EXTRA_CA_CERTS, REQUESTS_CA_BUNDLE, SSL_CERT_FILE 환경변수 설정됨

## 주의사항
- Poetry 환경 밖 global에서는 Python 3.12 사용 (py launcher 기본값)
- WSL에서도 별도 인증서 설정 필요 (`~/certs/`)
