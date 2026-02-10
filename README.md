# Agentic AI Knowledge Graph Explorer

Agentic AI 도메인의 연구(논문)와 서비스(프레임워크/라이브러리) 간 공진화를 추적하는 지식 그래프 시스템.

LangGraph + Neo4j를 결합하여 대화형 에이전트가 지식 그래프를 탐색·요약·확장하고, Critic Agent가 품질을 관리하며, Prompt Optimizer가 자동으로 프롬프트를 개선합니다.

## 핵심 기능

- **지식 그래프 탐색**: 11개 Principle → Method → Implementation → Standard 계층 구조 탐색
- **의도 맞춤 검색**: 11가지 intent 기반 Cypher/Vector/Hybrid 자동 전환
- **웹 검색 확장**: 그래프에 없는 정보는 Tavily로 검색 후 KG 추가 제안
- **문서 수집**: URL/PDF 업로드 → 자동 청킹·임베딩·KG 관계 추출
- **Critic Agent**: 15개 평가 기준으로 에이전트 출력 품질 평가
- **Prompt Optimizer**: 실패 패턴 탐지 → 가설 기반 프롬프트 변형 → Human-in-the-Loop 이중 게이트 승인
- **그래프 시각화**: Overview 모드 + 쿼리 결과 기반 서브그래프 시각화

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline                        │
│  Intent Classifier → Search Planner → Graph Retriever       │
│                                          ↓                  │
│                                   [has results?]            │
│                                    ↓          ↓             │
│                                  YES     Web Search         │
│                                    ↓          ↓             │
│                                   Synthesizer               │
└─────────────────────────────────────────────────────────────┘
        ↕                ↕                    ↕
┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐
│   Neo4j KG   │ │  ChromaDB    │ │  Critic → Optimizer      │
│  (67+ nodes) │ │  (vectors)   │ │  (evaluate → improve)    │
└──────────────┘ └──────────────┘ └──────────────────────────┘
```

### Knowledge Graph 구조

```
Principle (11개 불변)
    ↑ ADDRESSES {role, weight}
  Method (33+ 연구 기법)
    ↑ IMPLEMENTS {support_level, evidence}
Implementation (16+ 프레임워크/서비스)
    ↑ COMPLIES_WITH {role, level}
StandardVersion (표준 버전)
    ↑ HAS_VERSION
  Standard (표준)
```

### 11 Principles

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

## 프로젝트 구조

```
agentic-kg-explorer/
├── config/                     # 설정
│   ├── settings.py            # Pydantic Settings
│   ├── intents.yaml           # 11개 intent 정의
│   ├── cypher_templates.yaml  # 20+ Cypher 템플릿
│   ├── providers.yaml         # LLM/Embedding provider
│   ├── evaluation_criteria.yaml # 15개 평가 기준
│   └── test_queries.yaml      # 프롬프트 최적화용 테스트 쿼리
├── src/
│   ├── graph/                 # Neo4j 클라이언트
│   ├── agents/                # LangGraph 파이프라인
│   │   ├── state.py          # AgentState (11 fields)
│   │   ├── graph.py          # 5-node conditional pipeline
│   │   ├── providers/        # LLM provider 추상화 (OpenAI, Anthropic, Gemini)
│   │   └── nodes/            # intent_classifier, search_planner,
│   │                         # graph_retriever, web_search, synthesizer
│   ├── critic/                # Critic Agent (Phase 4)
│   │   ├── criteria.py       # YAML 기반 평가 기준 로드
│   │   ├── scorer.py         # LLM 기반 점수 산정
│   │   └── evaluator.py      # CriticEvaluator 오케스트레이션
│   ├── optimizer/             # Prompt Optimizer (Phase 5)
│   │   ├── models.py         # FailurePattern, PromptVariant, PromptVersion
│   │   ├── analyzer.py       # 실패 패턴 탐지
│   │   ├── generator.py      # 프롬프트 변형 생성
│   │   ├── runner.py         # 테스트 실행 + 평가
│   │   └── registry.py       # 프롬프트 버전 관리
│   ├── ingestion/             # 문서 수집 (P2)
│   │   ├── crawler.py        # URL/PDF 텍스트 추출
│   │   ├── chunker.py        # 문서 청킹
│   │   └── linker.py         # Document → KG 관계 추출
│   ├── retrieval/             # 벡터 검색
│   │   ├── providers/        # Embedding provider 추상화
│   │   └── vector_store.py   # ChromaDB wrapper
│   ├── api/                   # FastAPI REST API
│   │   ├── routes.py         # /query, /evaluations, /optimizer/* 등
│   │   └── schemas.py        # Pydantic request/response models
│   └── ui/                    # Streamlit UI
│       └── app.py            # Chat + Graph Viz + Gate 1/2 + Version History
├── neo4j/                     # Cypher 스크립트
│   ├── schema.cypher         # 제약조건/인덱스
│   ├── seed_data.cypher      # 초기 데이터
│   └── seed_evaluation.cypher # 평가 기준 seed
├── scripts/                   # CLI 도구
│   ├── generate_entity_catalog.py
│   ├── generate_embeddings.py
│   ├── test_agent.py
│   ├── seed_evaluation_criteria.py
│   ├── ingest_document.py
│   ├── analyze_failures.py
│   └── run_optimization.py
├── docs/
│   ├── schema.md             # 전체 스키마 정의서
│   ├── phase4-critic-agent-design.md
│   ├── phase5-prompt-optimizer-design.md
│   └── db_experiment_plan.md # Graph vs Vector vs Hybrid 검증 계획
├── pyproject.toml
└── .env.example
```

## 시작하기

### 1. 환경 설정

```bash
git clone <repository-url>
cd agentic-kg-explorer
poetry install
cp .env.example .env
# .env 편집: Neo4j, LLM API keys, Tavily API key 설정
```

### 2. Neo4j 설정

```env
NEO4J_URI=neo4j://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key

TAVILY_API_KEY=tvly-xxxxx    # 웹 검색용 (선택)
OPENAI_API_KEY=sk-...        # 임베딩용
```

### 3. 데이터베이스 초기화

```bash
# 스키마 + Seed 데이터
poetry run python scripts/load_sample_data.py

# 평가 기준 시드
poetry run python scripts/seed_evaluation_criteria.py

# 엔티티 카탈로그 생성
poetry run python scripts/generate_entity_catalog.py

# 벡터 임베딩 생성
poetry run python scripts/generate_embeddings.py
```

### 4. 실행

```bash
# FastAPI 백엔드
poetry run uvicorn src.api.app:app --reload --port 8000

# Streamlit UI
poetry run streamlit run src/ui/app.py
```

### 5. CLI 테스트

```bash
# 에이전트 쿼리 테스트
poetry run python scripts/test_agent.py --query "What is ReAct?"

# 실패 패턴 분석
poetry run python scripts/analyze_failures.py --agent synthesizer

# 프롬프트 최적화
poetry run python scripts/run_optimization.py --agent synthesizer
```

## 개발 로드맵

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ | 스키마 설계, Neo4j 세팅, Seed 데이터 (67 nodes, 79 rels) |
| Phase 2 | ✅ | LangGraph 파이프라인, Multi-provider LLM, Vector 검색, FastAPI, Streamlit UI |
| Phase 3 | ✅ | Web Search (Tavily), 유저 승인 UI, 그래프 시각화 |
| P0/P1 | ✅ | Confidence 재설계, Intent 확장 (11개), Cypher YAML 외부화, Entity Catalog |
| Phase 4 | ✅ | Critic Agent (15 평가 기준, LLM 점수 산정, API/UI 통합) |
| P2 | ✅ | Document Pipeline (URL/PDF 크롤링, 청킹, KG 자동 연결) |
| Phase 5 | ✅ | Prompt Optimizer (실패 분석, 변형 생성, 테스트, Human-in-the-Loop Gate 1/2, API/UI) |

## 문제 해결

### Neo4j 연결 오류
- URI: `neo4j://` 사용 (not `neo4j+s://`)
- Windows: `trust="TRUST_ALL_CERTIFICATES"` 설정 필요

### Windows vs macOS vs WSL
- Windows: `kg` 명령어로 가상환경 활성화
- macOS: `poetry run python ...`
- WSL: `poetry run python ...` 또는 `.venv/bin/activate`

### 한글 인코딩 오류
```powershell
$env:PYTHONIOENCODING="utf-8"
```

## License

MIT License
