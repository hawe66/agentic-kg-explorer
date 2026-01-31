# Agentic AI Knowledge Graph Explorer

Agentic AI 도메인의 연구(논문)와 서비스(프레임워크/라이브러리) 간 공진화를 추적하는 지식 그래프 시스템.

LangGraph + Neo4j를 결합하여 대화형 에이전트가 지식 그래프를 탐색·요약·확장하는 시스템입니다.

## 🎯 프로젝트 목표

### 핵심 가치
1. **공진화 추적**: 논문에서 제안된 Method가 어떤 Implementation에서 구현되는지 추적
2. **표준 준수 모니터링**: Implementation이 어떤 Standard를 준수하는지 추적
3. **증거 기반**: 모든 관계에 문서 근거(Claim) 연결

### 주요 기능
- 📚 **지식 그래프 탐색**: 개념 간 관계를 따라 정보 탐색
- 🔍 **의도 맞춤 요약**: 질문 의도에 따른 맞춤형 답변
- 🌐 **웹 검색 확장**: 그래프에 없는 정보는 웹에서 찾아 제안
- 🔬 **Critic Agent**: 에이전트 평가 및 지침 개선
- ⚡ **Prompt Optimizer**: 자동 프롬프트 최적화

## 🏗️ 아키텍처

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                        User Query                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Intent   │→ │ Search   │→ │ Graph    │→ │Synthesize│     │
│  │Classifier│  │ Planner  │  │ Retriever│  │          │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                      │              │                       │
│                      ▼              ▼                       │
│               ┌──────────┐  ┌──────────┐                    │
│               │   Web    │  │  Critic  │                    │
│               │ Expander │  │  Agent   │                    │
│               └──────────┘  └──────────┘                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Neo4j                               │
│          Knowledge Graph (Principles ↔ Methods              │
│                ↔ Implementations ↔ Standards)               │
└─────────────────────────────────────────────────────────────┘
```

### Knowledge Graph 핵심 구조

```
Principle (11개 불변)
    ↑ ADDRESSES {role, weight}
  Method (연구 기법)
    ↑ IMPLEMENTS {support_level, evidence}
Implementation (프레임워크/서비스)
    ↑ COMPLIES_WITH {role, level}
StandardVersion (표준 버전)
    ↑ HAS_VERSION
  Standard (표준)
```

### 11 Principles (불변)

| ID | Principle | Description |
|---|-----------|-------------|
| p:perception | Perception | 환경으로부터 정보 수집/해석 |
| p:memory | Memory | 정보 저장, 검색, 갱신 |
| p:planning | Planning | 목표 분해 및 실행 순서 생성 |
| p:reasoning | Reasoning | 논리적 추론으로 결론 도출 |
| p:tool-use | Tool Use & Action | 외부 도구 선택 및 호출 |
| p:reflection | Reflection | 자기 평가 및 개선 |
| p:grounding | Grounding | 외부 지식 기반 사실적 출력 |
| p:learning | Learning | 피드백/경험 기반 능력 향상 |
| p:multi-agent | Multi-Agent Collaboration | 에이전트 간 협력/조정 |
| p:guardrails | Guardrails | 안전성, 보안, 규정 준수 |
| p:tracing | Tracing | 실행 흐름 관찰 및 분석 |

## 📁 프로젝트 구조

```
agentic-kg-explorer/
├── README.md               # 프로젝트 개요 및 시작 가이드
├── CHANGELOG.md            # 버전별 변경 이력
├── CLAUDE.md               # Claude Code 컨텍스트 (프로젝트 가이드)
├── config/                 # 설정 관리
│   ├── settings.py        # Pydantic Settings
│   └── __init__.py
├── src/
│   ├── graph/             # Neo4j 클라이언트 & 스키마 (✅ 구현됨)
│   │   ├── client.py      # Neo4jClient (연결, CRUD, 도메인 쿼리)
│   │   ├── schema.py      # Pydantic 모델 (Node/Relationship 타입)
│   │   └── __init__.py
│   ├── agents/            # LangGraph 에이전트들 (✅ 기본 파이프라인 구현됨)
│   │   ├── __init__.py    # 모듈 exports (create_agent_graph, run_agent, AgentState)
│   │   ├── state.py       # AgentState TypedDict (11 fields)
│   │   ├── graph.py       # LangGraph 파이프라인 (linear 4-node flow)
│   │   ├── README.md      # 에이전트 아키텍처 문서
│   │   ├── providers/     # LLM provider 추상화 (✅ 구현됨)
│   │   │   ├── base.py    # LLMProvider ABC
│   │   │   ├── router.py  # provider 라우팅 + fallback + SSL
│   │   │   ├── openai.py  # OpenAI provider
│   │   │   ├── anthropic.py # Anthropic provider
│   │   │   └── gemini.py  # Gemini provider
│   │   └── nodes/         # 개별 노드 구현
│   │       ├── intent_classifier.py   # 쿼리 의도 분류
│   │       ├── search_planner.py      # Cypher 템플릿 선택 (7개)
│   │       ├── graph_retriever.py     # Neo4j 쿼리 실행
│   │       └── synthesizer.py         # 자연어 답변 생성
│   ├── retrieval/         # 벡터 검색 (✅ ChromaDB + OpenAI embeddings)
│   │   ├── embedder.py   # OpenAI embedding client
│   │   ├── vector_store.py # ChromaDB wrapper (VectorStore, VectorSearchResult)
│   │   └── __init__.py
│   ├── optimizer/         # Prompt Optimizer (🔜 Phase 5)
│   └── api/               # FastAPI 엔드포인트 (🔜 Phase 2)
├── data/
│   ├── raw/               # 원본 데이터 (비어있음)
│   ├── processed/         # 처리된 데이터 (비어있음)
│   └── sample_data.py     # 샘플 데이터 정의
├── neo4j/                 # Cypher 스크립트 (✅ 완료)
│   ├── schema.cypher      # 제약조건 & 인덱스 (37 statements)
│   ├── seed_data.cypher   # 초기 데이터 (11 Principles, 31 Methods, 16 Implementations, 149 statements)
│   └── validation_queries.cypher  # 검증 쿼리
├── scripts/               # 유틸리티 스크립트 (✅ 구현됨)
│   ├── load_sample_data.py  # DB 초기화 & 데이터 로드
│   └── test_queries.py      # 쿼리 테스트 (10 test cases)
├── prompts/               # 프롬프트 템플릿 (🔜 Phase 2)
├── tests/                 # 테스트 (✅ Jupyter notebook)
│   └── test_kg.ipynb      # Knowledge Graph 테스트 노트북 (driver.execute_query() 예제)
├── docs/
│   └── schema.md          # 전체 스키마 정의서
├── pyproject.toml         # Poetry 의존성 관리
└── .env.example           # 환경변수 템플릿
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# Poetry 설치 (없는 경우)
curl -sSL https://install.python-poetry.org | python3 -

# 프로젝트 클론
git clone <repository-url>
cd agentic-kg-explorer

# 의존성 설치
poetry install

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 Neo4j 연결 정보 설정
```

### 2. Neo4j 설정

**Option A: Neo4j Aura (권장)**
1. [Neo4j Aura](https://neo4j.com/cloud/aura/) 에서 무료 인스턴스 생성
2. Connection URI와 비밀번호를 `.env`에 설정

```env
# Neo4j Aura 기본 설정
NEO4J_URI=neo4j://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# LLM Provider (openai | anthropic | gemini)
LLM_PROVIDER=gemini
# LLM_MODEL=gemini-2.0-flash  # 생략 시 provider 기본값 사용
# LLM_FALLBACK_PROVIDER=openai

# API Keys (사용할 provider에 해당하는 키만 설정)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=your-gemini-api-key
```

**중요**: Windows 환경에서 Neo4j Aura 사용 시:
- URI는 `neo4j://` 사용 (`neo4j+s://` 아님)
- `src/graph/client.py`의 `connect()` 메서드에 `trust="TRUST_ALL_CERTIFICATES"` 추가됨
- 이는 개발 환경용이며, 프로덕션에서는 적절한 인증서 설정 필요

**Option B: Local Docker**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# .env 설정
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
```

### 3. 데이터베이스 초기화

```bash
# 스키마 + Seed 데이터 로드
poetry run python scripts/load_sample_data.py

# 기존 데이터를 삭제하고 새로 로드
poetry run python scripts/load_sample_data.py --clear
```

### 4. 쿼리 테스트

**Option A: 자동 테스트 스크립트**
```bash
# 샘플 쿼리 실행 및 결과 확인
poetry run python scripts/test_queries.py
```

예상 출력:
```
=== Database Statistics ===
Total Nodes: 67
Total Relationships: 79

Nodes by Label:
  Document: 3
  Implementation: 16
  Method: 31
  Principle: 11
  Standard: 3
  StandardVersion: 3

Relationships by Type:
  ADDRESSES: 43
  COMPLIES_WITH: 2
  HAS_VERSION: 3
  IMPLEMENTS: 23
  INTEGRATES_WITH: 3
  PROPOSES: 3
  USES: 2
```

**Option B: Jupyter 노트북으로 대화형 탐색**
```bash
# Jupyter 실행
poetry run jupyter notebook tests/test_kg.ipynb
```

노트북에서 제공하는 기능:
- **Section 1-12**: 기본 Cypher 쿼리 예제 (Principle → Method → Implementation 경로 등)
- **Section 13**: `driver.execute_query()` API 5가지 패턴
  - 간단한 읽기 쿼리
  - 파라미터 바인딩
  - 쓰기 작업
  - 결과 변환 (custom transformer)
  - 복잡한 경로 쿼리

## 🔧 문제 해결 (Troubleshooting)

### Neo4j 연결 오류

**증상**: `Unable to retrieve routing information` 오류
```
neo4j.exceptions.ServiceUnavailable: Unable to retrieve routing information
```

**해결 방법**:
1. `.env` 파일에서 URI 확인: `neo4j://` 사용 (not `neo4j+s://`)
2. `src/graph/client.py`의 `connect()` 메서드 확인:
   ```python
   self.driver = GraphDatabase.driver(
       uri,
       auth=(username, password),
       trust="TRUST_ALL_CERTIFICATES"  # Windows/Aura 환경용
   )
   ```
3. Neo4j Aura 콘솔에서 인스턴스 상태 확인 (Running 상태여야 함)

### Windows vs WSL 환경

**Poetry 가상환경 위치**:
- Windows: `C:\Users\{username}\AppData\Local\pypoetry\Cache\virtualenvs\`
- WSL: 프로젝트 폴더 내 `.venv/`

**Python 실행 방법**:
```bash
# Windows (PowerShell)
python scripts/test_queries.py

# WSL
poetry run python scripts/test_queries.py
# 또는 .venv 활성화 후
source .venv/bin/activate
python scripts/test_queries.py
```

### 한글 인코딩 오류

**증상**: `UnicodeEncodeError: 'cp949' codec` 오류

**해결 방법**: PowerShell에서 UTF-8 인코딩 설정
```powershell
$env:PYTHONIOENCODING="utf-8"
```

---

## 📋 Phase 1 완료 요약

Phase 1에서 구축된 지식 그래프의 핵심 통계:

| 항목 | 수량 | 세부사항 |
|------|------|---------|
| **노드** | 67개 | Principle(11) + Method(31) + Implementation(16) + Standard(3) + StandardVersion(3) + Document(3) |
| **관계** | 79개 | ADDRESSES(43) + IMPLEMENTS(23) + PROPOSES(3) + HAS_VERSION(3) + COMPLIES_WITH(2) + USES(2) + INTEGRATES_WITH(3) |
| **Principle 커버리지** | 100% | 11개 Principle 모두 Method와 연결됨 |
| **고아 노드** | 0개 | 모든 Implementation이 최소 1개 Method와 연결됨 |
| **코드 라인** | 1,100+ | client.py(520) + schema.py(437) + seed_data.cypher(1,100+) |

### 주요 달성 사항
1. **완전한 도메인 모델링**: 11 Principles를 중심으로 Agentic AI 도메인 전체 구조화
2. **데이터 품질 검증**: 10개 테스트 케이스로 관계 무결성 확인
3. **재현 가능한 초기화**: 스크립트 기반 자동 DB 세팅
4. **개발자 친화적 도구**: Jupyter 노트북으로 쿼리 예제 제공

### 알려진 제약사항
- Neo4j Aura 연결 시 `trust="TRUST_ALL_CERTIFICATES"` 설정 필요 (Windows 환경)
- URI에서 `+s` 제거 필요 (`neo4j://` 사용)
- 현재 31개 Method 중 22개가 논문 미연결 (향후 Document 노드 확장 필요)

---

## 🔧 개발 로드맵

### Phase 1: 기반 구축 ✅ **완료**
- [x] 스키마 설계 완료 (`docs/schema.md`)
- [x] Neo4j 클라이언트 구현 (`src/graph/client.py` - 520 lines)
- [x] Pydantic 모델 정의 (`src/graph/schema.py` - 437 lines)
- [x] Seed 데이터 작성 (`neo4j/seed_data.cypher` - 31 Methods, 16 Implementations)
- [x] 초기화 스크립트 (`scripts/load_sample_data.py`)
- [x] 테스트 스크립트 (`scripts/test_queries.py`)
- [x] Jupyter 노트북 (`tests/test_kg.ipynb` with `driver.execute_query()` examples)
- [x] 데이터 품질 검증 완료 (0 orphan nodes, 11 principles 100% covered)

### Phase 2: 핵심 플로우 🔧 **진행 중**
- [x] LangGraph 기본 구조 (4-node linear pipeline: Intent → Search → Retrieve → Synthesize)
- [x] Multi-provider LLM 추상화 (OpenAI, Anthropic, Gemini)
- [x] 에이전트 테스트 스크립트 (`scripts/test_agent.py`)
- [ ] Provider config 외부화 (YAML 기반 선언적 전환)
- [x] 벡터 검색 연동 (ChromaDB + OpenAI embeddings, 3-mode retrieval)
- [x] FastAPI REST endpoints (POST /query, GET /health, /stats, /graph/principles)
- [ ] Streamlit UI

### Phase 3: 확장 기능 🔜
- [ ] Web Search Expander
- [ ] 유저 승인 UI
- [ ] 그래프 시각화

### Phase 4: Critic Agent 🔜
- [ ] 평가 원칙/방법 정의
- [ ] 평가 로직 구현
- [ ] 지침 버저닝 시스템

### Phase 5: Prompt Optimizer 🔜
- [ ] Failure Analyzer
- [ ] Variant Generator
- [ ] Test Runner + Critic 연동

### Phase 6: 고도화 🔜
- [ ] RAG 고도화
- [ ] 자동 데이터 수집
- [ ] 성능 최적화

## 🎨 핵심 설계 결정

### 1. Standard 버전 분리
- `Standard` + `StandardVersion` 노드 분리
- 이유: MCP(날짜 기반), A2A(semver), OTel(experimental 상태) 등 다양한 버전 정책 수용

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
- `ADDRESSES`: Method → Principle (Method가 Principle을 달성/개선)
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

## 📊 유용한 Cypher 쿼리

### Principle → Method → Implementation 전체 경로

```cypher
MATCH path = (p:Principle)<-[:ADDRESSES]-(m:Method)<-[:IMPLEMENTS]-(i:Implementation)
RETURN p.name, m.name, collect(i.name) AS implementations
ORDER BY p.name;
```

### 특정 Method를 구현하는 Implementation

```cypher
MATCH (i:Implementation)-[r:IMPLEMENTS]->(m:Method {id: 'm:react'})
RETURN i.name, r.support_level, r.evidence;
```

### Standard 준수 현황

```cypher
MATCH (i:Implementation)-[r:COMPLIES_WITH]->(sv:StandardVersion)-[:HAS_VERSION]-(s:Standard)
RETURN s.name, sv.version, i.name, r.role, r.level;
```

### Paper 없는 Method 찾기 (데이터 품질 체크)

```cypher
MATCH (m:Method)
WHERE NOT (m)<-[:PROPOSES]-(:Document:Paper)
  AND m.seminal_source IS NULL
RETURN m.id, m.name;
```

## 🔍 경계 규칙 (중요)

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

## 🛠️ 개발 시 참고사항

1. **스키마 변경 시**: `docs/schema.md` 먼저 업데이트
2. **새 Method 추가 시**: 반드시 `ADDRESSES` 관계로 Principle 연결
3. **새 Implementation 추가 시**: 반드시 `IMPLEMENTS` 관계로 Method 연결
4. **Principle 추가/수정 금지**: 11개는 불변
5. **전체 컨텍스트**: `CLAUDE.md` 참조

## 📄 License

MIT License
