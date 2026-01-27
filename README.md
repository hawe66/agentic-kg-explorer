# Agentic AI Knowledge Graph Explorer

LangGraph + Neo4j를 결합한 개인 지식 그래프 탐색 시스템

## 🎯 프로젝트 목표

Agentic AI 관련 논문, 아티클, 메모를 그래프로 구조화하고, 대화형 에이전트가 탐색·요약·확장을 도와주는 시스템.

### 핵심 기능
- 📚 **지식 그래프 탐색**: 개념 간 관계를 따라 정보 탐색
- 🔍 **의도 맞춤 요약**: 질문 의도에 따른 맞춤형 답변
- 🌐 **웹 검색 확장**: 그래프에 없는 정보는 웹에서 찾아 제안
- 🔬 **Critic Agent**: 에이전트 평가 및 지침 개선
- ⚡ **Prompt Optimizer**: 자동 프롬프트 최적화

## 🏗️ 아키텍처

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
│   Documents ←→ Concepts ←→ Authors ←→ Sources               │
└─────────────────────────────────────────────────────────────┘
```
  
### AI Knowledge Graph 핵심 구조

```
Principle (11개 불변)
    ↑ ADDRESSES
  Method (연구 기법)
    ↑ IMPLEMENTS
Implementation (프레임워크/서비스)
    ↑ COMPLIES_WITH
StandardVersion (표준 버전)
```

### 11 Principles

| Principle | Description |
|-----------|-------------|
| Perception | 환경으로부터 정보 수집/해석 |
| Memory | 정보 저장, 검색, 갱신 |
| Planning | 목표 분해 및 실행 순서 생성 |
| Reasoning | 논리적 추론으로 결론 도출 |
| Tool Use & Action | 외부 도구 선택 및 호출 |
| Reflection | 자기 평가 및 개선 |
| Grounding | 외부 지식 기반 사실적 출력 |
| Learning | 피드백/경험 기반 능력 향상 |
| Multi-Agent Collaboration | 에이전트 간 협력/조정 |
| Guardrails | 안전성, 보안, 규정 준수 |
| Tracing | 실행 흐름 관찰 및 분석 |

## 📁 프로젝트 구조

```
agentic-kg-explorer/
├── config/                 # 설정 관리
│   └── settings.py
├── src/
│   ├── agents/            # LangGraph 에이전트들
│   ├── graph/             # Neo4j 클라이언트 & 스키마
│   ├── retrieval/         # RAG 컴포넌트
│   ├── optimizer/         # Prompt Optimizer
│   └── api/               # FastAPI 엔드포인트
├── data/
│   ├── raw/               # 원본 데이터
│   ├── processed/         # 처리된 데이터
│   └── sample_data.py     # 샘플 데이터
├── prompts/               # 프롬프트 템플릿
├── scripts/               # 유틸리티 스크립트
├── tests/                 # 테스트
└── docs/                  # 문서
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# Poetry 설치 (없는 경우)
curl -sSL https://install.python-poetry.org | python3 -

# 의존성 설치
cd agentic-kg-explorer
poetry install

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 Neo4j 및 LLM API 키 설정
```

### 2. Neo4j 설정

**Option A: Neo4j Aura (권장)**
1. [Neo4j Aura](https://neo4j.com/cloud/aura/) 에서 무료 인스턴스 생성
2. Connection URI와 비밀번호를 `.env`에 설정

**Option B: Local Docker**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 3. 샘플 데이터 로드

```bash
poetry run python scripts/load_sample_data.py --clear
```

### 4. 쿼리 테스트

```bash
poetry run python scripts/test_queries.py
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# - Neo4j connection details
# - LLM API keys (OpenAI or Anthropic)
```

### 4. Database Setup

```bash
# Initialize database with schema and seed data
python src/db_setup.py

# Or with options:
python src/db_setup.py --clear    # Clear existing data first
python src/db_setup.py --stats    # Show statistics only
```

### 5. Verify Setup

```bash
# Check database statistics
python src/db_setup.py --stats
```

Expected output:
```
=== Database Statistics ===
Total Nodes: ~50
Total Relationships: ~80

Nodes by Label:
  Principle: 11
  Standard: 3
  StandardVersion: 3
  Method: ~25
  Implementation: ~15
  Document: 3
```

## Project Structure

```
agentic-ai-kg/
├── docs/
│   └── schema.md           # 스키마 정의서
├── neo4j/
│   ├── schema.cypher       # 제약조건/인덱스
│   └── seed_data.cypher    # 초기 데이터
├── src/
│   ├── db_setup.py         # DB 초기화
│   ├── models/             # Pydantic 모델 (Phase 2)
│   ├── api/                # FastAPI 엔드포인트 (Phase 2)
│   └── agents/             # LangGraph 에이전트 (Phase 2)
├── requirements.txt
├── .env.example
└── README.md
```

## Development Roadmap

### Phase 1: 기반 구축 ✅
- [x] 스키마 설계 완료
- [x] Neo4j 세팅 스크립트
- [x] Seed 데이터 (11 Principles, 25+ Methods, 15+ Implementations)
- [ ] 수동 데이터 입력 검증

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
- [ ] 지침 버저닝 시스템

### Phase 5: Prompt Optimizer
- [ ] Failure Analyzer
- [ ] Variant Generator
- [ ] Test Runner + Critic 연동

### Phase 6: 고도화
- [ ] RAG 고도화
- [ ] 자동 데이터 수집
- [ ] 성능 최적화

## Key Design Decisions

### 1. Standard 버전 관리
- `Standard` + `StandardVersion` 분리
- MCP (날짜 기반), A2A (semver), OTel (experimental 상태) 추적

### 2. Method 분류
- `method_family`: 1차 분류 (통제된 vocabulary)
- `method_type`: 형태 분류 (prompt_pattern, agent_control_loop 등)
- `granularity`: atomic vs composite

### 3. 관계 의미 분리
- `ADDRESSES`: Method → Principle (role: primary/secondary)
- `IMPLEMENTS`: Implementation → Method (support_level)
- `COMPLIES_WITH`: Implementation → StandardVersion (role, level)

### 4. 증거 기반
- 모든 관계는 `Claim` 노드로 추적 가능
- `DocumentChunk`에서 근거 연결

## Common Cypher Queries

### Principle → Method → Implementation 경로

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


## 🔧 개발 로드맵

- [x] **Phase 1**: 기반 구축 (Neo4j, 스키마, 샘플 데이터)
- [ ] **Phase 2**: 핵심 플로우 (LangGraph, RAG, FastAPI)
- [ ] **Phase 3**: 확장 기능 (Web Search, 유저 승인 UI)
- [ ] **Phase 4**: Critic Agent (평가 체계, 지침 버저닝)
- [ ] **Phase 5**: Prompt Optimizer (Human-in-the-loop 최적화)

## License

MIT License