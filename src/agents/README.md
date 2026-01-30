# LangGraph Agent Pipeline

Phase 2의 핵심 기능인 LangGraph 기반 지식 그래프 탐색 에이전트입니다.

## 아키텍처

```
User Query
    ↓
[Intent Classifier] - 질문 의도 분류 (lookup/path/comparison/expansion)
    ↓
[Search Planner] - 전략 수립: graph_only | vector_first | hybrid
    ↓
[Graph Retriever] - Neo4j Cypher 실행 AND/OR ChromaDB 벡터 검색
    ↓
[Synthesizer] - 자연어 답변 생성 (graph + vector results)
    ↓
Answer + Sources + Confidence
```

## State Schema

```python
class AgentState(TypedDict):
    # Input
    user_query: str

    # Intent Classification
    intent: Literal["lookup", "path", "comparison", "expansion"]
    entities: list[str]

    # Search Planning
    search_strategy: dict  # Cypher template + parameters + retrieval_type

    # Graph Retrieval
    kg_results: list[dict]
    cypher_executed: list[str]

    # Vector Search
    vector_results: Optional[list[dict]]  # ChromaDB similarity results

    # Synthesis
    answer: str
    sources: list[dict]
    confidence: float

    # Error Handling
    error: Optional[str]
```

## 질문 유형 (Intent)

### 1. Lookup - 단일 개념 조회
- "What is ReAct?"
- "Tell me about LangChain"
- "Explain Planning principle"

### 2. Path - 관계 탐색
- "What methods address Planning principle?"
- "Which frameworks implement ReAct?"
- "What principles does AutoGen support?"

### 3. Comparison - 개념 비교
- "Compare LangChain and CrewAI"
- "Difference between ReAct and Chain-of-Thought"

### 4. Expansion - 그래프 외부 정보
- "Latest agent frameworks in 2025"
- *(Phase 3에서 Web Search로 연결)*

## 사용 방법

### Python API

```python
from src.agents import run_agent

# 단일 쿼리 실행
result = run_agent("What is ReAct?")

print(result["answer"])
print(f"Confidence: {result['confidence']}")
print(f"Sources: {result['sources']}")
```

### CLI 테스트

```bash
# 단일 쿼리 테스트
python scripts/test_agent.py --query "What is ReAct?"

# 전체 테스트 스위트 실행
python scripts/test_agent.py

# Verbose 모드 (Cypher 쿼리 표시)
python scripts/test_agent.py --query "What methods address Planning?" --verbose
```

## 파일 구조

```
src/agents/
├── __init__.py          # 모듈 export
├── state.py             # AgentState 정의
├── graph.py             # LangGraph 파이프라인 (create_agent_graph, run_agent)
├── providers/           # LLM provider 추상화
│   ├── __init__.py
│   ├── base.py          # LLMProvider ABC (generate interface)
│   ├── router.py        # provider 라우팅 + fallback + SSL
│   ├── openai.py        # OpenAI (기본: gpt-4o-mini)
│   ├── anthropic.py     # Anthropic (기본: claude-3-5-sonnet-20241022)
│   └── gemini.py        # Gemini (기본: gemini-2.5-flash)
└── nodes/
    ├── __init__.py
    ├── intent_classifier.py   # LLM 기반 의도 분류
    ├── search_planner.py      # Cypher 쿼리 템플릿 선택
    ├── graph_retriever.py     # Neo4j 쿼리 실행
    └── synthesizer.py         # LLM 기반 답변 생성
```

## Cypher 쿼리 템플릿

Search Planner가 intent와 entity type에 따라 적절한 템플릿을 선택합니다:

- `lookup_method`: Method 노드 조회
- `lookup_implementation`: Implementation 노드 조회
- `lookup_principle`: Principle 노드 조회
- `path_principle_to_methods`: Principle → Methods 경로
- `path_method_to_implementations`: Method → Implementations 경로
- `path_implementation_to_principles`: Implementation → Principles 경로
- `comparison`: 두 엔티티 비교

## 벡터 검색 (Vector Search)

Search Planner가 intent와 ChromaDB 가용성에 따라 retrieval 전략을 결정합니다:

| Strategy | 조건 | 동작 |
|----------|------|------|
| `graph_only` | 기본값, ChromaDB 비활성 | Cypher만 실행 |
| `vector_first` | expansion intent 또는 Cypher 템플릿 없음 | ChromaDB 검색 → Neo4j 보강 |
| `hybrid` | lookup/path + ChromaDB 활성 | Cypher + ChromaDB 병렬 → 결과 병합 |

### 벡터 DB 초기화

```bash
# OpenAI embedding으로 KG 노드 임베딩 생성 → ChromaDB 저장
poetry run python scripts/generate_embeddings.py
```

ChromaDB는 `data/chroma/`에 영구 저장됩니다. 삭제하면 `graph_only`로 자동 폴백합니다.

## 환경 변수

`.env` 파일에 다음 변수가 필요합니다:

```env
# Neo4j
NEO4J_URI=neo4j://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# LLM Provider 설정
LLM_PROVIDER=gemini              # openai | anthropic | gemini
# LLM_MODEL=gemini-2.0-flash     # 생략 시 provider 기본값 사용
# LLM_FALLBACK_PROVIDER=openai   # 선택사항

# API Keys (사용할 provider 것만 설정)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=your-key
```

## 예시 출력

```
Query: What methods address Planning principle?
Intent: path
Entities: ['Planning']

Answer:
The Planning principle is addressed by several methods:

1. **ReAct** (primary, weight: 1.0)
   - Combines reasoning and acting in iterative loops
   - Implemented by: LangChain (core), CrewAI (first-class)

2. **Plan-and-Execute** (primary, weight: 1.0)
   - Separates planning and execution phases
   - Implemented by: LangChain (core)

3. **LATS** (primary, weight: 0.9)
   - Tree-search based planning with language models
   - Implemented by: LangChain (template)

Confidence: 0.9
Sources: 3 nodes (Principle:Planning, Method:ReAct, Method:Plan-and-Execute)
```

## Provider Fallback 동작

Provider 해결 순서: Primary (`LLM_PROVIDER`) → Fallback (`LLM_FALLBACK_PROVIDER`) → Heuristic

LLM API 호출 실패 시:
- Intent Classifier: 휴리스틱 기반 분류 (키워드 매칭)
- Synthesizer: 간단한 텍스트 포매팅

## Phase 3 연동 계획

- `expansion` intent 시 Web Search Expander 호출
- 그래프에 없는 최신 정보를 웹에서 검색
- 사용자 승인 후 그래프에 추가 가능

## 디버깅

```python
result = run_agent("Your query")

# Check executed Cypher queries
print(result["cypher_executed"])

# Check raw KG results
print(result["kg_results"])

# Check error
if result["error"]:
    print(f"Error: {result['error']}")
```
