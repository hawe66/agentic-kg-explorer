# Phase 4: Critic Agent + P2 Document Pipeline — Design Document

> Phase 4는 Critic Agent 시스템을 구축하고, P2의 문서 파이프라인을 함께 구현한다.
> Critic Agent가 문서 품질과 KG 연결을 평가할 수 있으므로 자연스러운 결합이다.

---

## 1. 목표 요약

### Phase 4: Critic Agent
1. **EvaluationCriteria** — 11 Principles에서 도출한 평가 기준
2. **Evaluation** — 에이전트 출력 평가 및 결과 저장
3. **FailurePattern** — 반복 실패 패턴 탐지 (Phase 5 준비)
4. **Guideline Versioning** — 프롬프트 버전 관리

### P2: Document Pipeline
1. **범용 문서 크롤러** — URL/PDF에서 텍스트 추출
2. **Local docs 업로드 UI** — Streamlit에서 파일 업로드
3. **Document → KG 자동 연결** — LLM으로 문서-Method/Implementation 관계 추출

---

## 2. 통합 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCUMENT PIPELINE (P2)                      │
│  URL/PDF → Crawler → Chunking → Embedding → ChromaDB            │
│                         ↓                                        │
│                   LLM Extraction                                 │
│                         ↓                                        │
│              Document → KG Linkage                               │
│         (PROPOSES Method, DESCRIBES Implementation)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RUNTIME PIPELINE                            │
│  User Query → Intent → Search → Retrieve → Web → Synthesize     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CRITIC EVALUATION                           │
│  - Answer quality scoring (4-dim → N-dim)                       │
│  - Data sufficiency check                                       │
│  - Save Evaluation node to Neo4j                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                         축적 (N회)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PATTERN ANALYSIS (Phase 5)                   │
│  - Detect FailurePatterns                                       │
│  - Generate PromptVersion candidates                            │
│  - Human approval gate                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Graph Schema 확장

### 3.1 Neo4j Schema (`neo4j/schema.cypher` 추가)

```cypher
// =============================================
// Phase 4: Critic Agent Schema
// =============================================

// EvaluationCriteria: 평가 기준 (Principle에서 도출)
CREATE CONSTRAINT ec_id IF NOT EXISTS FOR (ec:EvaluationCriteria) REQUIRE ec.id IS UNIQUE;
CREATE INDEX ec_principle IF NOT EXISTS FOR (ec:EvaluationCriteria) ON (ec.principle_id);
CREATE INDEX ec_agent IF NOT EXISTS FOR (ec:EvaluationCriteria) ON (ec.agent_target);

// Evaluation: 개별 평가 결과
CREATE CONSTRAINT eval_id IF NOT EXISTS FOR (e:Evaluation) REQUIRE e.id IS UNIQUE;
CREATE INDEX eval_agent IF NOT EXISTS FOR (e:Evaluation) ON (e.agent_name);
CREATE INDEX eval_created IF NOT EXISTS FOR (e:Evaluation) ON (e.created_at);

// FailurePattern: 반복 실패 패턴 (Phase 5)
CREATE CONSTRAINT fp_id IF NOT EXISTS FOR (fp:FailurePattern) REQUIRE fp.id IS UNIQUE;

// PromptVersion: 프롬프트 버전 (Phase 5)
CREATE CONSTRAINT pv_id IF NOT EXISTS FOR (pv:PromptVersion) REQUIRE pv.id IS UNIQUE;
CREATE INDEX pv_agent IF NOT EXISTS FOR (pv:PromptVersion) ON (pv.agent_name);
CREATE INDEX pv_active IF NOT EXISTS FOR (pv:PromptVersion) ON (pv.is_active);

// Relationships
// (EvaluationCriteria)-[:DERIVED_FROM]->(Principle)
// (Evaluation)-[:USES_CRITERIA]->(EvaluationCriteria)
// (FailurePattern)-[:IDENTIFIED_FROM]->(Evaluation)  -- Phase 5
// (PromptVersion)-[:ADDRESSES]->(FailurePattern)     -- Phase 5
```

### 3.2 Node Properties

```yaml
EvaluationCriteria:
  id: string              # "ec:reasoning-cot-completeness"
  name: string            # "Chain-of-Thought Completeness"
  description: string     # "추론 단계가 명시적으로 나열되어야 함"
  principle_id: string    # "p:reasoning" (FK)
  agent_target: string    # "synthesizer" | "intent_classifier" | "*"
  scoring_rubric: string  # JSON or YAML format rubric
  weight: float           # 0.0-1.0, importance in composite score
  version: string         # "1.0.0"
  is_active: boolean      # true
  created_at: datetime

Evaluation:
  id: string              # "eval:2026-02-04-001"
  agent_name: string      # "synthesizer"
  query: string           # Original user query
  response: string        # Agent's response (truncated)
  scores: string          # JSON: {"ec:reasoning-cot": 0.8, "ec:source-citation": 0.9}
  composite_score: float  # Weighted average
  feedback: string        # LLM-generated feedback
  created_at: datetime
  conversation_id: string # Optional session tracking

# Phase 5 nodes (schema only, not implemented yet)
FailurePattern:
  id: string              # "fp:missing-source-citation"
  pattern_type: string    # "output_quality" | "reasoning" | "retrieval"
  description: string
  frequency: int
  affected_agents: list[string]
  root_cause_hypotheses: list[string]
  suggested_fixes: list[string]
  created_at: datetime

PromptVersion:
  id: string              # "pv:synthesizer@1.2.0"
  agent_name: string
  version: string
  content_hash: string    # SHA256 of prompt content
  prompt_path: string     # Path to prompt file or inline
  is_active: boolean
  user_approved: boolean
  parent_version: string  # "pv:synthesizer@1.1.0"
  performance_delta: float # +0.05 (improvement from parent)
  created_at: datetime
```

---

## 4. EvaluationCriteria 초기 세트

11 Principles에서 도출한 평가 기준 (에이전트별):

### 4.1 Synthesizer 평가 기준

| ID | Name | Principle | Description | Weight |
|----|------|-----------|-------------|--------|
| ec:answer-relevance | Answer Relevance | p:reasoning | 질문에 직접적으로 답변하는가 | 0.20 |
| ec:source-citation | Source Citation | p:grounding | KG 출처를 명시하는가 | 0.15 |
| ec:factual-accuracy | Factual Accuracy | p:grounding | KG 데이터와 일치하는가 | 0.20 |
| ec:reasoning-steps | Reasoning Steps | p:reasoning | 논리적 추론 과정이 보이는가 | 0.15 |
| ec:completeness | Completeness | p:memory | 관련 정보를 누락하지 않았는가 | 0.15 |
| ec:conciseness | Conciseness | p:planning | 불필요한 정보 없이 간결한가 | 0.10 |
| ec:safety | Safety | p:guardrails | 유해/부적절 내용이 없는가 | 0.05 |

### 4.2 Intent Classifier 평가 기준

| ID | Name | Principle | Description | Weight |
|----|------|-----------|-------------|--------|
| ec:intent-accuracy | Intent Accuracy | p:perception | 의도를 정확히 분류했는가 | 0.40 |
| ec:entity-extraction | Entity Extraction | p:perception | 엔티티를 정확히 추출했는가 | 0.40 |
| ec:scope-detection | Scope Detection | p:guardrails | out_of_scope를 적절히 감지하는가 | 0.20 |

### 4.3 Search Planner 평가 기준

| ID | Name | Principle | Description | Weight |
|----|------|-----------|-------------|--------|
| ec:template-selection | Template Selection | p:planning | 적절한 Cypher 템플릿을 선택했는가 | 0.50 |
| ec:retrieval-mode | Retrieval Mode | p:tool-use | graph/vector/hybrid 선택이 적절한가 | 0.30 |
| ec:parameter-binding | Parameter Binding | p:reasoning | 파라미터를 정확히 바인딩했는가 | 0.20 |

---

## 5. Critic Agent 구현

### 5.1 파일 구조

```
src/
├── critic/
│   ├── __init__.py
│   ├── evaluator.py       # CriticEvaluator class
│   ├── criteria.py        # Load/manage EvaluationCriteria
│   ├── scorer.py          # Multi-criteria scoring logic
│   └── feedback.py        # LLM-based feedback generation
├── agents/
│   ├── nodes/
│   │   └── critic.py      # Critic node for pipeline (optional)
│   └── graph.py           # Add critic node after synthesizer
config/
└── evaluation_criteria.yaml  # Criteria definitions
```

### 5.2 CriticEvaluator Class

```python
class CriticEvaluator:
    """Evaluates agent outputs against EvaluationCriteria."""

    def __init__(self):
        self.criteria = load_criteria_from_yaml()
        self.llm = get_provider()

    def evaluate(
        self,
        agent_name: str,
        query: str,
        response: str,
        context: dict,  # kg_results, vector_results, etc.
    ) -> Evaluation:
        """Score response against all criteria for this agent."""
        relevant_criteria = self.get_criteria_for_agent(agent_name)
        scores = {}

        for criterion in relevant_criteria:
            score = self.score_criterion(criterion, query, response, context)
            scores[criterion.id] = score

        composite = self.calculate_composite(scores, relevant_criteria)
        feedback = self.generate_feedback(scores, relevant_criteria)

        return Evaluation(
            id=generate_eval_id(),
            agent_name=agent_name,
            query=query,
            response=response[:500],
            scores=json.dumps(scores),
            composite_score=composite,
            feedback=feedback,
            created_at=datetime.now(),
        )

    def score_criterion(
        self,
        criterion: EvaluationCriteria,
        query: str,
        response: str,
        context: dict,
    ) -> float:
        """Score a single criterion using LLM or heuristics."""
        # Use LLM to score based on rubric
        prompt = f"""
        Evaluate this response on the criterion: {criterion.name}

        Criterion: {criterion.description}
        Rubric: {criterion.scoring_rubric}

        Query: {query}
        Response: {response}

        Score from 0.0 to 1.0:
        """
        # ... LLM call and parse score
```

### 5.3 Pipeline Integration

Option A: **Post-pipeline hook** (non-blocking)
```python
def run_agent(query: str) -> dict:
    result = graph.invoke(initial_state)

    # Async evaluation (doesn't block response)
    asyncio.create_task(evaluate_and_store(result))

    return result
```

Option B: **Pipeline node** (blocking, adds latency)
```python
# In graph.py
graph.add_node("critic", critic_node)
graph.add_edge("synthesize_answer", "critic")
```

**Recommendation**: Start with Option A (post-pipeline hook) to avoid latency impact.

---

## 6. P2: Document Pipeline

### 6.1 파일 구조

```
src/
├── ingestion/
│   ├── __init__.py
│   ├── crawler.py         # URL/PDF text extraction
│   ├── chunker.py         # Text chunking strategies
│   └── linker.py          # Document → KG relationship extraction
scripts/
├── ingest_document.py     # CLI for single document
└── ingest_batch.py        # Batch ingestion
src/ui/
└── app.py                 # Add upload widget
```

### 6.2 Crawler (`src/ingestion/crawler.py`)

```python
class DocumentCrawler:
    """Extract text from URL or PDF."""

    def crawl_url(self, url: str) -> Document:
        """Fetch and extract text from URL."""
        # Use httpx + BeautifulSoup or Tavily extract
        pass

    def crawl_pdf(self, file_path: Path) -> Document:
        """Extract text from PDF using PyMuPDF."""
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        return Document(
            title=file_path.stem,
            content=text,
            source_path=str(file_path),
        )
```

### 6.3 Document → KG Linker (`src/ingestion/linker.py`)

```python
class DocumentLinker:
    """Extract relationships between Document and KG entities."""

    def link_document(self, doc: Document) -> list[Relationship]:
        """Use LLM to identify Methods/Implementations mentioned."""

        # Load entity catalog for context
        catalog = load_entity_catalog()

        prompt = f"""
        Given this document, identify which Agentic AI concepts it discusses.

        Document: {doc.content[:3000]}

        Known entities in our Knowledge Graph:
        - Methods: {catalog['methods'][:20]}
        - Implementations: {catalog['implementations']}

        For each mentioned entity, specify the relationship:
        - PROPOSES: Document introduces/proposes this method
        - EVALUATES: Document evaluates/benchmarks this method
        - DESCRIBES: Document describes this implementation
        - USES: Document uses this implementation

        Output JSON:
        [
          {{"entity_id": "m:react", "relationship": "EVALUATES", "evidence": "quote..."}},
          ...
        ]
        """
        # ... LLM call and parse
```

### 6.4 Streamlit Upload UI

```python
# In src/ui/app.py sidebar
with st.expander("📄 Add Document"):
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    url_input = st.text_input("Or enter URL")

    if st.button("Process"):
        if uploaded_file:
            doc = crawler.crawl_pdf(uploaded_file)
        elif url_input:
            doc = crawler.crawl_url(url_input)

        # Extract and show proposed links
        links = linker.link_document(doc)
        st.json(links)

        if st.button("Approve & Add to KG"):
            # Save document node and relationships
            pass
```

---

## 7. 구현 순서

### Step 1: Schema & Seed (Day 1)
- [ ] `neo4j/schema.cypher` — Add EvaluationCriteria, Evaluation constraints
- [ ] `config/evaluation_criteria.yaml` — Define initial 15 criteria
- [ ] `neo4j/seed_evaluation.cypher` — Seed EvaluationCriteria nodes

### Step 2: Critic Core (Day 2)
- [ ] `src/critic/criteria.py` — Load criteria from YAML/Neo4j
- [ ] `src/critic/scorer.py` — LLM-based scoring per criterion
- [ ] `src/critic/evaluator.py` — CriticEvaluator orchestration
- [ ] `src/critic/feedback.py` — Generate improvement feedback

### Step 3: Pipeline Integration (Day 3)
- [ ] `src/agents/graph.py` — Add post-pipeline evaluation hook
- [ ] `src/api/routes.py` — Add `/evaluations` endpoint
- [ ] `src/ui/app.py` — Show evaluation scores in response

### Step 4: Document Crawler (Day 4)
- [ ] `src/ingestion/crawler.py` — URL + PDF extraction
- [ ] `src/ingestion/chunker.py` — Text chunking
- [ ] `scripts/ingest_document.py` — CLI tool

### Step 5: Document Linker (Day 5)
- [ ] `src/ingestion/linker.py` — LLM-based entity linking
- [ ] `src/ui/app.py` — Upload widget + approval UI
- [ ] Integration test with sample PDF

### Step 6: Testing & Polish (Day 6)
- [ ] End-to-end test: query → response → evaluation → storage
- [ ] End-to-end test: PDF → chunks → embedding → KG links
- [ ] Update CHANGELOG.md, CLAUDE.md

---

## 8. 검증 방법

### Critic Agent 검증
```bash
# 1. Generate evaluation criteria
poetry run python scripts/seed_evaluation_criteria.py

# 2. Run agent and check evaluation
poetry run python scripts/test_agent.py --query "What is ReAct?" --evaluate

# 3. Query evaluations
# GET /evaluations?agent=synthesizer&limit=10
```

### Document Pipeline 검증
```bash
# 1. Ingest a PDF
poetry run python scripts/ingest_document.py --pdf papers/react.pdf

# 2. Check proposed links
# Streamlit UI shows: "Document mentions: m:react (PROPOSES), impl:langchain (USES)"

# 3. Approve and verify in Neo4j
MATCH (d:Document)-[r]->(m:Method) RETURN d.title, type(r), m.name
```

---

## 9. 의존성

```toml
# pyproject.toml additions
pymupdf = "^1.24.0"        # Already added
beautifulsoup4 = "^4.12.0" # For URL crawling
```

---

## 10. 리스크 & 완화

| Risk | Mitigation |
|------|------------|
| LLM scoring variance | Use rubrics with examples; consider few-shot prompts |
| Evaluation latency | Run async, don't block response |
| Document linking accuracy | Show proposals for human approval before committing |
| Storage growth (Evaluation nodes) | Add retention policy; archive old evaluations |
