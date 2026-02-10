# Phase 5: Prompt Optimizer — Design Document

> Phase 5는 Critic Agent의 평가 결과를 기반으로 프롬프트를 자동 최적화하는 시스템을 구축한다.
> Human-in-the-Loop 이중 게이트로 안전하게 프롬프트 진화를 관리한다.

---

## 1. 목표 요약

1. **Failure Analyzer** — 반복 실패 패턴 탐지 및 FailurePattern 생성
2. **Variant Generator** — 실패 가설 기반 프롬프트 변형 생성 (3개)
3. **Test Runner** — 테스트 쿼리로 변형 평가, 최고 성능 선택
4. **Prompt Registry** — 프롬프트 버전 관리, 활성화/롤백
5. **Review UI** — Human-in-the-Loop 승인 게이트

---

## 2. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVALUATION ACCUMULATION                      │
│  Phase 4 Critic → Evaluation nodes in Neo4j (N회 축적)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                         trigger (N >= threshold)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FAILURE ANALYZER                             │
│  - Query low-scoring evaluations by agent                        │
│  - Cluster by criterion (ec:source-citation, ec:reasoning, etc.) │
│  - Generate FailurePattern with root_cause_hypotheses            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GATE 1: HYPOTHESIS REVIEW                    │
│  User reviews/edits root_cause_hypotheses before proceeding      │
│  Options: Approve / Edit / Reject / Add more hypotheses          │
└─────────────────────────────────────────────────────────────────┘
                              │
                         (approved)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VARIANT GENERATOR                            │
│  - Load current prompt for affected agent                        │
│  - LLM generates 3 prompt variants addressing hypotheses         │
│  - Each variant has: diff, rationale, expected_improvement       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TEST RUNNER                                  │
│  - Run test queries (from config/test_queries.yaml)              │
│  - Evaluate each variant with Critic                             │
│  - Compare composite scores vs baseline                          │
│  - Rank variants by performance_delta                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GATE 2: PROMPT APPROVAL                      │
│  User reviews best variant:                                      │
│  - Side-by-side diff with current prompt                         │
│  - Test results summary                                          │
│  - Options: Approve / Edit / Reject / Try another variant        │
└─────────────────────────────────────────────────────────────────┘
                              │
                         (approved)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROMPT REGISTRY                              │
│  - Create PromptVersion node in Neo4j                            │
│  - Link: (PromptVersion)-[:ADDRESSES]->(FailurePattern)          │
│  - Set is_active=true, deactivate previous version               │
│  - Update prompt file on disk                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Graph Schema (이미 Phase 4에서 추가됨)

```cypher
// FailurePattern: 반복 실패 패턴
CREATE CONSTRAINT fp_id IF NOT EXISTS
FOR (fp:FailurePattern) REQUIRE fp.id IS UNIQUE;

CREATE INDEX fp_type IF NOT EXISTS
FOR (fp:FailurePattern) ON (fp.pattern_type);

// PromptVersion: 프롬프트 버전
CREATE CONSTRAINT pv_id IF NOT EXISTS
FOR (pv:PromptVersion) REQUIRE pv.id IS UNIQUE;

CREATE INDEX pv_agent IF NOT EXISTS
FOR (pv:PromptVersion) ON (pv.agent_name);

CREATE INDEX pv_active IF NOT EXISTS
FOR (pv:PromptVersion) ON (pv.is_active);

// Relationships
// (FailurePattern)-[:IDENTIFIED_FROM]->(Evaluation)
// (PromptVersion)-[:ADDRESSES]->(FailurePattern)
// (PromptVersion)-[:PARENT_OF]->(PromptVersion)
```

### Node Properties

```yaml
FailurePattern:
  id: string              # "fp:synthesizer:source-citation:2026-02"
  pattern_type: string    # "output_quality" | "reasoning" | "retrieval" | "classification"
  agent_name: string      # "synthesizer"
  criterion_id: string    # "ec:source-citation"
  description: string     # "Synthesizer consistently fails to cite KG sources"
  frequency: int          # Number of low-score evaluations
  sample_queries: [string] # Example queries that triggered this
  avg_score: float        # Average score for this criterion
  root_cause_hypotheses: [string]  # LLM-generated hypotheses
  suggested_fixes: [string]        # Potential prompt changes
  status: string          # "detected" | "reviewing" | "addressing" | "resolved"
  created_at: datetime
  resolved_at: datetime

PromptVersion:
  id: string              # "pv:synthesizer@1.2.0"
  agent_name: string      # "synthesizer"
  version: string         # "1.2.0" (semver)
  prompt_hash: string     # SHA256 of prompt content
  prompt_path: string     # "prompts/synthesizer/v1.2.0.txt"
  is_active: boolean      # Only one active per agent
  user_approved: boolean  # Human approved this version
  parent_version: string  # "pv:synthesizer@1.1.0"
  performance_delta: float # +0.05 improvement from parent
  test_results: string    # JSON summary of test run
  rationale: string       # Why this change was made
  created_at: datetime
  approved_at: datetime
  approved_by: string     # User identifier
```

---

## 4. 파일 구조

```
src/
├── optimizer/
│   ├── __init__.py
│   ├── analyzer.py       # FailureAnalyzer class
│   ├── generator.py      # VariantGenerator class
│   ├── runner.py         # TestRunner class
│   ├── registry.py       # PromptRegistry class
│   └── models.py         # Dataclasses (FailurePattern, PromptVariant, etc.)
├── ui/
│   └── app.py            # Add optimization review panels
config/
├── test_queries.yaml     # Test queries per intent type
└── prompts/              # Versioned prompt storage
    ├── synthesizer/
    │   ├── current.txt   # Symlink to active version
    │   ├── v1.0.0.txt
    │   └── v1.1.0.txt
    ├── intent_classifier/
    └── search_planner/
scripts/
├── analyze_failures.py   # CLI to trigger failure analysis
├── generate_variants.py  # CLI to generate prompt variants
└── run_optimization.py   # Full optimization pipeline
```

---

## 5. 컴포넌트 상세

### 5.1 Failure Analyzer (`src/optimizer/analyzer.py`)

```python
class FailureAnalyzer:
    """Detect recurring failure patterns from evaluations."""

    def __init__(self, threshold: float = 0.6, min_samples: int = 5):
        self.threshold = threshold  # Score below this = failure
        self.min_samples = min_samples  # Min failures to create pattern

    def analyze(self, agent_name: str = None) -> list[FailurePattern]:
        """Query evaluations, cluster failures, generate patterns."""
        # 1. Query low-scoring evaluations from Neo4j
        # 2. Group by (agent_name, criterion_id)
        # 3. For groups with count >= min_samples:
        #    - Generate FailurePattern
        #    - Use LLM to hypothesize root causes
        # 4. Save FailurePattern to Neo4j
        pass

    def _generate_hypotheses(
        self,
        agent_name: str,
        criterion: str,
        sample_queries: list[str],
        sample_responses: list[str],
    ) -> list[str]:
        """Use LLM to generate root cause hypotheses."""
        prompt = f"""
        The {agent_name} agent consistently scores low on "{criterion}".

        Sample failing queries and responses:
        {self._format_samples(sample_queries, sample_responses)}

        Generate 2-3 hypotheses for why this might be happening.
        Focus on prompt-level issues that could be fixed.

        Output as JSON list: ["hypothesis 1", "hypothesis 2", ...]
        """
        # LLM call
        pass
```

### 5.2 Variant Generator (`src/optimizer/generator.py`)

```python
class VariantGenerator:
    """Generate prompt variants to address failure patterns."""

    def generate_variants(
        self,
        failure_pattern: FailurePattern,
        num_variants: int = 3,
    ) -> list[PromptVariant]:
        """Generate prompt variants addressing the failure."""
        # 1. Load current prompt for agent
        current_prompt = self._load_current_prompt(failure_pattern.agent_name)

        # 2. Generate variants with LLM
        prompt = f"""
        Current prompt for {failure_pattern.agent_name}:
        ---
        {current_prompt}
        ---

        This prompt has a recurring issue: {failure_pattern.description}

        Root cause hypotheses:
        {failure_pattern.root_cause_hypotheses}

        Generate {num_variants} improved versions of this prompt.
        Each version should:
        1. Address at least one hypothesis
        2. Be a complete replacement prompt
        3. Include a brief rationale

        Output as JSON:
        [
          {{
            "prompt": "full new prompt text...",
            "rationale": "why this change helps",
            "addresses_hypotheses": [0, 1]
          }},
          ...
        ]
        """
        # LLM call, parse variants
        pass
```

### 5.3 Test Runner (`src/optimizer/runner.py`)

```python
class TestRunner:
    """Run test queries and evaluate prompt variants."""

    def __init__(self):
        self.evaluator = get_evaluator()

    def run_tests(
        self,
        agent_name: str,
        variants: list[PromptVariant],
        test_queries: list[str] = None,
    ) -> list[TestResult]:
        """Run tests for each variant, return ranked results."""
        if test_queries is None:
            test_queries = self._load_test_queries(agent_name)

        results = []

        # Test baseline (current prompt)
        baseline_scores = self._test_variant(agent_name, None, test_queries)

        # Test each variant
        for variant in variants:
            variant_scores = self._test_variant(agent_name, variant, test_queries)
            delta = self._calculate_delta(baseline_scores, variant_scores)

            results.append(TestResult(
                variant=variant,
                scores=variant_scores,
                baseline_scores=baseline_scores,
                performance_delta=delta,
            ))

        # Rank by performance delta
        results.sort(key=lambda r: r.performance_delta, reverse=True)
        return results

    def _test_variant(
        self,
        agent_name: str,
        variant: PromptVariant | None,
        test_queries: list[str],
    ) -> dict[str, float]:
        """Run test queries with a specific prompt variant."""
        # Temporarily swap prompt if variant provided
        # Run queries through pipeline
        # Collect evaluation scores
        # Return average scores per criterion
        pass
```

### 5.4 Prompt Registry (`src/optimizer/registry.py`)

```python
class PromptRegistry:
    """Manage prompt versions and activation."""

    def __init__(self, prompts_dir: Path = None):
        self.prompts_dir = prompts_dir or Path("config/prompts")

    def get_current_version(self, agent_name: str) -> PromptVersion:
        """Get currently active prompt version."""
        pass

    def get_version_history(self, agent_name: str) -> list[PromptVersion]:
        """Get all versions for an agent."""
        pass

    def create_version(
        self,
        agent_name: str,
        content: str,
        parent_version: str,
        failure_pattern_id: str,
        rationale: str,
        test_results: dict,
    ) -> PromptVersion:
        """Create new prompt version (not yet active)."""
        # 1. Calculate next version number
        # 2. Write prompt to file
        # 3. Create PromptVersion node in Neo4j
        # 4. Link to FailurePattern
        pass

    def activate_version(self, version_id: str, approved_by: str) -> bool:
        """Activate a prompt version (deactivate previous)."""
        # 1. Set is_active=false on current active
        # 2. Set is_active=true, user_approved=true on new version
        # 3. Update symlink: current.txt -> vX.Y.Z.txt
        pass

    def rollback(self, agent_name: str, to_version: str = None) -> bool:
        """Rollback to previous version."""
        # If to_version not specified, rollback to parent
        pass
```

---

## 6. Test Queries Configuration

```yaml
# config/test_queries.yaml

synthesizer:
  - query: "What is ReAct?"
    expected_intent: lookup
    expected_entities: ["m:react"]
    min_confidence: 0.7

  - query: "What methods address Planning?"
    expected_intent: path
    min_sources: 2

  - query: "Compare LangChain and CrewAI"
    expected_intent: comparison
    expected_entities: ["impl:langchain", "impl:crewai"]

intent_classifier:
  - query: "What is CoT?"
    expected_intent: lookup
    expected_entities: ["m:cot"]

  - query: "How many methods are there?"
    expected_intent: aggregation

  - query: "What's the weather?"
    expected_intent: out_of_scope

search_planner:
  - query: "Which frameworks implement ReAct?"
    expected_template: "path_method_to_impl"
    expected_retrieval: "hybrid"

graph_retriever:
  - query: "What is ReAct?"
    min_results: 1
    no_error: true
```

---

## 7. UI Components (✅ 구현 완료)

> 아래는 `src/ui/app.py`에 구현된 Streamlit UI 구성요소 설명이다.

### 7.1 Failure Patterns Panel (Sidebar)

사이드바 "Prompt Optimizer" 섹션의 `🔧 Failure Patterns` expander 내부:

- **Analyze Failures** 버튼 → `FailureAnalyzer(threshold=0.6).analyze()` 호출
- 탐지된 패턴 목록: agent 이름, criterion, frequency, avg score (색상 코딩)
- 각 패턴에 **Start Optimization** 버튼 → Gate 1으로 전환
- **📜 Version History** 버튼 → 버전 이력 패널 열기

### 7.2 Gate 1: Hypothesis Review Panel

메인 영역에 `🔬 Gate 1: Review Hypotheses` expander로 표시:

- 패턴 요약: agent, criterion, description, frequency, avg score
- Sample failing queries (접기 가능)
- **편집 가능한 가설 목록** (`st.text_input` per hypothesis)
- 새 가설 추가 입력란
- 액션 버튼:
  - **✅ Approve & Generate Variants** → 가설 업데이트 → `VariantGenerator.generate_variants()` → `TestRunner.run_tests()` → Gate 2 전환
  - **❌ Reject Pattern** → 패턴 resolved 처리, 상태 초기화

### 7.3 Gate 2: Prompt Approval Panel

메인 영역에 `🎯 Gate 2: Approve Prompt Change` expander로 표시:

- 성능 순 정렬된 변형 목록 (🏆 표시로 최고 성능 강조)
- 각 변형:
  - Performance delta (색상 코딩), pass rate, passed/failed count
  - Rationale 설명
  - **📋 View Prompt Diff** — 현재 vs 제안 프롬프트 side-by-side `st.code` 비교
  - 비최고 변형에 **Select Variant** 버튼 (순서 재배치)
- 액션 버튼:
  - **✅ Approve & Activate** → `VariantGenerator.apply_variant()` → `PromptRegistry.activate_version()` → 패턴 resolved
  - **🔄 Re-run Tests** → 동일 변형 재테스트
  - **❌ Reject All** → 상태 초기화

### 7.4 Version History Panel

메인 영역에 `📜 Prompt Version History` expander로 표시:

- Agent 선택 드롭다운 (synthesizer, intent_classifier, search_planner, graph_retriever)
- 버전별: version 번호, 🟢 ACTIVE 표시, performance delta, approved 날짜, rationale
- 비활성 버전에 **⏪ Rollback** 버튼
- **Close History** 버튼

### 7.5 Session State (Optimizer)

```python
optimizer_patterns: list          # 탐지된 failure patterns
optimizer_selected_pattern: obj   # Gate 1에서 선택된 패턴
optimizer_edited_hypotheses: list # 편집된 가설 목록
optimizer_variants: list          # 생성된 prompt variants
optimizer_test_results: list      # 테스트 결과
optimizer_gate: str | None        # None | "gate1" | "gate2"
optimizer_show_history: bool      # 버전 이력 패널 표시 여부
```

---

## 8. 구현 순서

### Step 1: Models & Registry ✅
- [x] `src/optimizer/models.py` — Dataclasses
- [x] `src/optimizer/registry.py` — PromptRegistry
- [x] `config/prompts/` — Initial prompt files extracted from code

### Step 2: Failure Analyzer ✅
- [x] `src/optimizer/analyzer.py` — FailureAnalyzer
- [x] `scripts/analyze_failures.py` — CLI tool

### Step 3: Variant Generator ✅
- [x] `src/optimizer/generator.py` — VariantGenerator
- [x] `config/test_queries.yaml` — Test query definitions

### Step 4: Test Runner ✅
- [x] `src/optimizer/runner.py` — TestRunner
- [x] Integration with Critic evaluator

### Step 5: UI Integration ✅
- [x] Gate 1: Hypothesis review panel
- [x] Gate 2: Prompt approval panel
- [x] Failure patterns sidebar
- [x] Version history panel with rollback

### Step 6: API Endpoints ✅
- [x] 7 REST endpoints (`/optimizer/*`)
- [x] Pydantic schemas (`src/api/schemas.py`)

---

## 9. API Endpoints (✅ 구현 완료)

`src/api/routes.py`에 구현된 7개 엔드포인트:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/optimizer/patterns` | 실패 패턴 목록 (agent, status 필터) |
| `POST` | `/optimizer/analyze` | 실패 패턴 탐지 트리거 |
| `POST` | `/optimizer/patterns/{id}/approve` | Gate 1: 가설 승인 → 변형 생성 |
| `POST` | `/optimizer/test` | 변형 테스트 실행 |
| `POST` | `/optimizer/versions/{id}/activate` | Gate 2: 프롬프트 버전 활성화 |
| `POST` | `/optimizer/rollback` | 이전 버전으로 롤백 |
| `GET` | `/optimizer/versions` | Agent별 버전 이력 조회 |

### Pydantic Schemas (`src/api/schemas.py`)

**Request models:**
- `AnalyzeRequest` — agent (optional), threshold (default 0.6)
- `ApproveHypothesesRequest` — hypotheses (list[str])
- `TestVariantsRequest` — agent_name, pattern_id, variant_ids
- `ActivateVersionRequest` — approved_by (default "user")
- `RollbackRequest` — agent_name, to_version (optional)

**Response models:**
- `FailurePatternsResponse` — patterns list + count
- `GenerateVariantsResponse` — variants list + pattern_id
- `TestResultsResponse` — results list + best_variant_id
- `VersionHistoryResponse` — versions list + current_version + count

---

## 10. 리스크 & 완화

| Risk | Mitigation |
|------|------------|
| LLM generates poor variants | Human review gate before activation |
| Test queries not representative | Maintain diverse test set, allow user additions |
| Regression after activation | Easy rollback, track performance_delta |
| Over-optimization (overfitting) | Cross-validation with held-out queries |
| Prompt drift over versions | Version history, parent tracking, diff view |

---

## 11. 이론적 기반

| Paper | Key Idea | Our Application |
|-------|----------|-----------------|
| **APO** [Pryzant 2023] | Text gradients from failures | root_cause_hypotheses as gradients |
| **Self-Refine** [Madaan 2023] | Generate-Feedback-Refine | Critic feedback → Generator → Test |
| **Reflexion** [Shinn 2023] | Verbal reinforcement | Failure patterns as verbal feedback |
| **PromptWizard** [Agarwal 2024] | Instruction-Example co-optimization | Could extend to example selection |

---

## 12. Success Metrics

- **Pattern Resolution Rate**: % of FailurePatterns that reach "resolved" status
- **Prompt Improvement**: Average performance_delta of approved versions
- **Approval Rate**: % of generated variants that get approved (measures generation quality)
- **Rollback Rate**: % of activations that need rollback (should be low)
- **Time to Resolution**: Days from pattern detection to resolution

---

## 13. Scope: Prompts vs Cypher Templates

### Current Scope (Phase 5)

Phase 5 optimizes **LLM instruction prompts only**, not Cypher query templates.

```
┌─────────────────────────────────────┐
│  IN SCOPE: LLM Prompts              │
│  ─────────────────────────────────  │
│  • intent_classifier prompt         │
│  • search_planner prompt            │
│  • synthesizer prompt               │
│  • graph_retriever prompt           │
│                                     │
│  Location: src/agents/nodes/*.py    │
│  → Extract to: config/prompts/      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  OUT OF SCOPE: Cypher Templates     │
│  ─────────────────────────────────  │
│  • lookup_method                    │
│  • path_principle_methods           │
│  • comparison_impl                  │
│  • aggregation_* templates          │
│                                     │
│  Location: config/cypher_templates.yaml │
└─────────────────────────────────────┘
```

### Rationale for Separation

| Aspect | LLM Prompts | Cypher Templates |
|--------|-------------|------------------|
| **Nature** | Natural language instructions | Structured query patterns |
| **Optimization** | Style, clarity, examples | Correctness, efficiency |
| **LLM can improve?** | Yes (text generation) | Limited (needs schema knowledge) |
| **Failure mode** | Misunderstanding, verbosity | Wrong results, syntax errors |
| **Testing** | Subjective quality scores | Deterministic result validation |

### When Retrieval Fails

If `graph_retriever` scores low, the root cause is usually:

1. **Wrong template selected** → Fix `search_planner` prompt (IN SCOPE)
2. **Template itself is wrong** → Manual fix to YAML (OUT OF SCOPE)
3. **Entity not in KG** → Data issue, not optimization target

---

## 14. Future Extension: Cypher Template Optimization

> **Status**: Not planned for Phase 5. Consider for Phase 6+.

### Potential Approach

If we extend to Cypher optimization, it would be a **separate track**:

```
┌─────────────────────────────────────────────────────────────────┐
│                  CYPHER TEMPLATE OPTIMIZER                       │
│                  (Future Phase 6+)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Template        │  │ Template        │  │ Template        │
│ Selection       │  │ Correctness     │  │ Performance     │
│ Optimizer       │  │ Validator       │  │ Tuner           │
└─────────────────┘  └─────────────────┘  └─────────────────┘
│                    │                    │
│ - Which template   │ - Does query      │ - Index usage
│   for which intent │   return expected │ - LIMIT values
│ - Entity type      │   schema?         │ - Query complexity
│   detection rules  │ - Syntax valid?   │
└────────────────────┴────────────────────┴─────────────────────
```

### Cypher-Specific Challenges

1. **Schema Awareness**: LLM needs to know node labels, relationship types, property names
2. **Syntax Validation**: Must verify Cypher is executable before testing
3. **Result Validation**: Need ground-truth expected results, not just scores
4. **Performance Metrics**: Query execution time, index usage (requires EXPLAIN/PROFILE)

### Potential CypherTemplateVersion Schema

```yaml
CypherTemplateVersion:
  id: string              # "ct:lookup_method@1.2.0"
  template_name: string   # "lookup_method"
  version: string
  cypher: string          # The actual Cypher query
  parameters: [string]    # ["entity"]
  expected_labels: [string]  # ["Method"] - for validation
  is_active: boolean
  avg_execution_time_ms: float
  created_at: datetime
```

### When to Consider This

- After Phase 5 is stable and showing value
- If retrieval failures remain high despite prompt optimization
- If new entity types/relationships are frequently added
- If query performance becomes a bottleneck
