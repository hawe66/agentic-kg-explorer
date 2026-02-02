# GraphDB vs VectorDB vs Hybrid 효용성 검증 계획서

> 목표: **그래프DB(Neo4j 등)**, **VectorDB(FAISS/Qdrant/pgvector 등)**, **Hybrid(Vector → KG enrichment)** 각각의 강점/약점을 **동일한 테스트셋/동일한 계측**으로 비교해 “언제 무엇을 쓰는 게 이득인지”를 정량·정성으로 판단한다.

---

## 1) 검증 질문(Research Questions)

### RQ1. 그래프DB가 이기는 문제는 무엇인가?
- **정확한 엔티티/관계**가 중요한 문제(lookup/path/aggregation)에서
- Vector-only 대비 **정확도·재현성·설명가능성**이 더 좋은가?

### RQ2. VectorDB가 이기는 문제는 무엇인가?
- KG에 없는 표현/동의어/한국어/오타/우회표현 등에서
- Graph-only 대비 **회수율(recall)**이 더 좋은가?

### RQ3. Hybrid가 실제로 ‘합’ 이상의 가치를 내는가?
- Vector로 “seed”를 찾고 Graph로 1~3 hop 확장했을 때
- Vector-only/Graph-only를 **동시에 상회**하는 케이스가 충분히 많은가?

### RQ4. “데이터 충분성 판단(ABSTAIN)”이 모드별로 어떤가?
- Vector hit가 약하거나 반대개념일 때 **비판적으로 거절/질문**하는지
- 모드에 따라 환각/억지포장 비율이 달라지는지

---

## 2) 비교 모드 정의

### Mode A — Graph-only
- 엔티티 링크(Exact ID/Name/Alias) → Cypher로 관계/속성/다중홉 조회
- Vector 검색 사용하지 않음

### Mode B — Vector-only
- Vector 검색 TopK → 해당 chunk/노드 텍스트 기반으로 응답 생성
- Graph 확장(neo4j 연결) 사용하지 않음

### Mode C — Hybrid (Vector → Graph enrichment)
- Vector TopK로 seed 노드 확보
- seed node_id로 그래프 1~3 hop 확장(Principle/Method/Implementation/Standard 등)
- **Relevance Critic**로 seed/확장 결과를 필터링/재랭킹 후 응답

> 핵심: **Intent classifier를 ‘우회’하는 강제 모드 실행(oracle mode)**을 제공해서,
> “모드 자체의 효용”을 먼저 분리해 비교한다.  
> 이후 end-to-end(의도분류 포함) 평가를 별도 트랙으로 수행한다.

---

## 3) 벤치마크 데이터셋 설계

### 3.1 Query Taxonomy (카테고리)
각 카테고리는 “어느 DB가 이기기 쉬운지”를 의도적으로 포함한다.

1) **Exact Lookup**
- 예: `m:icl`, `impl:zep`, `doc:rag-2020`  
- 기대 승자: Graph-only

2) **Semantic / Paraphrase / Alias**
- 예: “컨텍스트 내 예시 학습”, “Graphiti가 뭐야?”, “retrieve-then-generate 방법”  
- 기대 승자: Vector-only 또는 Hybrid

3) **Multi-hop Path (2~3 hop)**
- 예: `p:memory → Method → Implementation`  
- 기대 승자: Hybrid(또는 Graph-only if entity가 명확)

4) **Aggregation / Ranking**
- 예: “가장 많은 Method를 구현하는 Implementation top3”  
- 기대 승자: Graph-only(혹은 Hybrid가 seed 없이도 가능해야 함)

5) **Missing Data / Should Abstain**
- 예: “MemGPT vs Zep 벤치마크 수치”, “LangChain 최신 버전”  
- 평가: **거절/부족 선언/추가질문**의 정확성

6) **Relevance Stress (약한/반대 매칭 유도)**
- 예: “parameter based learning”  
- 평가: Synthesizer가 **관련성 비판**을 수행하는지

7) **KR/EN mix + Typos**
- 예: “In context learnig”, “retrievel augmented generation”  
- 기대: Vector 기반 회복 + Graph enrichment

---

### 3.2 Gold(정답) 라벨 구조
최소 2단계를 권장한다.

- **Retrieval Gold**
  - relevant_nodes: `["m:rag", "doc:rag-2020"]` 같은 형태
  - relevant_edges(optional): `("m:rag","ADDRESSES","p:grounding")` 등
  - must_not_include(optional): 반대개념/무관 노드(예: “parameter-based learning”에서 `m:icl`은 “반대개념”으로 표시)

- **Answer Gold(선택)**
  - must_say: “KG에 없음/정확히 매칭 불가”
  - must_ask: “당신이 말한 parameter-based learning이 (fine-tuning/online learning/…) 중 무엇인지?”
  - forbidden: “근거 없는 수치 제시”, “무관 노드 나열로 포장”

> 초기에는 Retrieval Gold만으로도 충분히 효용 비교가 가능하고,
> Answer Gold는 “Synthesizer/Critic 개선” 단계에서 추가한다.

---

### 3.3 Dataset 포맷 예시 (YAML 권장)
`eval/datasets/queries.yaml`

```yaml
- id: Q_RAG_001
  category: exact_lookup
  query: "m:icl 설명해줘"
  gold:
    relevant_nodes: ["m:icl"]
  expectations:
    should_use: ["graph"]
    should_not_abstain: true

- id: Q_HYB_001
  category: multi_hop
  query: "p:memory를 address하는 Method와 그 구현체를 알려줘"
  gold:
    relevant_nodes: ["p:memory"]   # 최소 anchor
  expectations:
    should_use: ["hybrid", "graph"]
    should_not_abstain: true

- id: Q_REL_001
  category: relevance_stress
  query: "parameter based learning이 뭐야? (KG 기반으로만)"
  gold:
    relevant_nodes: []             # 직접 매칭 없음
  expectations:
    should_abstain: true
    must_say:
      - "knowledge graph does not contain"
    must_ask:
      - "What do you mean by"
    forbidden:
      - "ICL is an example"
````

---

## 4) 평가 지표(메트릭) 설계

### 4.1 Retrieval Metrics (정량)

* **Recall@K**: gold relevant_nodes를 TopK에서 얼마나 회수했나
* **Precision@K**: TopK 중 관련 노드 비율
* **MRR**: 첫 relevant가 몇 번째에 등장하는가
* **nDCG@K**(선택): relevance 등급(관련/약관련/반대개념)을 부여하면 유용

> Hybrid의 핵심은 **Recall 상승 + Precision 유지(또는 완만한 하락)**를 보이는지 여부.

### 4.2 Answer/Policy Metrics (정성→정량화 가능)

* **Abstain Accuracy**: “없어야 할 때 없다” + “있을 때 있다”
* **Relevance Critic Pass Rate**

  * weak match(score<τ)에서 “포장” 대신 “불충분 선언/질문”을 했는가
* **Grounding Rate**

  * 답변에서 언급한 핵심 주장들이 sources(노드/문서)에 매핑되는 비율

### 4.3 시스템 지표(운영 효율)

* p50/p95 latency (vector / graph / hybrid 각각)
* DB 호출 수, hop 수, topK
* 토큰 수(LLM 호출 있다면), 비용
* 오류율(쿼리 실패, 타임아웃)

---

## 5) 로그/트레이스 스키마(필수)

### 5.1 단일 실행 결과 레코드(JSONL)

`runs/{timestamp}_{mode}.jsonl`에 한 줄=한 쿼리 실행 결과 저장

```json
{
  "query_id": "Q_REL_001",
  "query": "parameter based learning이 뭐야? (KG 기반으로만)",
  "mode": "hybrid",
  "intent_pred": "expansion",
  "retrieval": {
    "vector_topk": [
      {"node_id":"m:icl","score":0.7048,"field":"name"},
      {"node_id":"doc:rag-2020","score":0.6575,"field":"abstract"}
    ],
    "graph_expansion": {
      "seed_ids": ["m:icl","doc:rag-2020"],
      "hop": 2,
      "cypher_executed": ["(vector enrichment)"],
      "nodes": ["m:icl","p:learning","m:rag","doc:rag-2020"]
    }
  },
  "critic": {
    "relevance_flags": [
      {"node_id":"m:icl","flag":"opposite_concept","reason":"non-parametric"},
      {"node_id":"m:rlhf","flag":"weak_related","reason":"alignment training, not defined term"}
    ],
    "data_sufficiency": "insufficient",
    "should_abstain": true
  },
  "answer": "...",
  "confidence": 0.12,
  "latency_ms": {
    "vector": 32,
    "graph": 58,
    "llm": 410
  },
  "errors": null
}
```

### 5.2 왜 이 구조가 중요한가?

* intent–행동 불일치(=expansion인데 vector만으로 포장)를 **로그에서 자동 감지** 가능
* confidence 산정 근거(Top score? evidence 수? critic 결과?)를 **분해 가능**

---

## 6) 코드 구조(권장 디렉터리)

```
project/
  retrieval/
    __init__.py
    vector/
      client.py           # VectorDB/FAISS/Qdrant/pgvector 추상화
      embed.py            # embedding 생성
      search.py           # search(query)->[hits]
    graph/
      client.py           # Neo4j driver wrapper
      cypher_templates.py # 표준 쿼리 모음
      expand.py           # expand(seed_ids, hop, filters)
    hybrid/
      pipeline.py         # vector->graph->rerank
      rerank.py           # critic 기반 필터/재랭킹
  agents/
    intent.py             # intent classifier (end-to-end 트랙)
    synthesizer.py        # answer generation
    critic.py             # relevance/data-sufficiency/confidence logic
  eval/
    datasets/
      queries.yaml
    runners/
      run_one.py          # 단일 쿼리 실행 (모드 강제)
      run_batch.py        # 배치 실행 (oracle)
    metrics/
      retrieval_metrics.py
      answer_metrics.py
    report/
      make_report.py      # markdown/html 리포트 생성
  scripts/
    build_embeddings.py
    build_vector_index.py
    snapshot_graph.py     # KG snapshot/export
    smoke_test.sh
  configs/
    eval.yaml
    db.yaml
```

---

## 7) 스크립트/실행 플로우

### 7.1 Index/DB 준비

1. 임베딩 생성/인덱스 구축

```bash
python scripts/build_embeddings.py --source data/docs --out data/embeddings.parquet
python scripts/build_vector_index.py --embeddings data/embeddings.parquet --index data/vector.index
```

2. 그래프 스냅샷(선택: 재현성)

```bash
python scripts/snapshot_graph.py --neo4j-uri ... --out snapshots/kg_neo4j_dump.jsonl
```

---

### 7.2 Oracle 모드 배치 평가(모드 강제)

```bash
python eval/runners/run_batch.py --dataset eval/datasets/queries.yaml --mode graph  --out runs/graph.jsonl
python eval/runners/run_batch.py --dataset eval/datasets/queries.yaml --mode vector --out runs/vector.jsonl
python eval/runners/run_batch.py --dataset eval/datasets/queries.yaml --mode hybrid --out runs/hybrid.jsonl
```

---

### 7.3 Metrics & Report

```bash
python eval/report/make_report.py \
  --dataset eval/datasets/queries.yaml \
  --runs runs/graph.jsonl runs/vector.jsonl runs/hybrid.jsonl \
  --out reports/efficacy_report.md
```

리포트에 포함할 것:

* 카테고리별 Recall@K / Precision@K
* Abstain Accuracy
* latency p50/p95
* “Hybrid가 이긴 쿼리 / 진 쿼리” Top N 예시 + 로그 스니펫

---

## 8) “효용성”을 드러내는 표준 쿼리 템플릿(카테고리별)

### 8.1 Graph-only에 유리한 쿼리

* **Direct node**

  * `m:icl`, `impl:zep`, `doc:rag-2020`
* **Aggregation**

  * “maturity=production Method 목록”
  * “Implementation이 구현하는 Method 수 TOP3”
* **Multi-hop path**

  * “p:memory → Method → Implementation”
  * “impl:zep → Method → Principle”

### 8.2 Vector-only에 유리한 쿼리

* 엔티티를 직접 말하지 않는 서술형

  * “retrieve-then-generate 방식”
  * “컨텍스트 내 예시 학습”
* alias/오타/한국어

  * “Graphiti”, “retrievel augmented generation”

### 8.3 Hybrid 효용을 드러내는 쿼리(핵심)

* vector로 seed를 찾고 그래프로 의미가 “열리는” 질문

  * “시간적 지식 그래프 기반 메모리 아키텍처가 뭔지 + 구현체”
  * “knowledge-graph 태그 method와 구현체”
  * “특정 principle을 만족하는 구현체 추천”

---

## 9) Hybrid의 ‘성공 조건’을 코드로 강제하기(중요)

Hybrid는 “연결을 더 가져오는 것”만으로는 가치가 없다.
**Critic 기반 relevance/data-sufficiency**가 필수다.

### 9.1 Relevance Critic 규칙(예시)

* vector_top1_score < 0.72 이면서
* topK 간 score gap이 작고(= 애매) AND
* seed들이 서로 다른 family로 흩어져 있으면
  → **“direct match 없음” + clarify/abstain** 우선

### 9.2 Confidence 산정(설명 가능해야 함)

권장 분해:

* `confidence = f( anchor_match, evidence_strength, agreement, coverage, critic_penalty )`

  * anchor_match: ID exact match / alias match / none
  * evidence_strength: top score, topK 평균, 스코어 분산
  * agreement: graph 확장 결과가 질문 타입과 정합한지
  * coverage: 필요한 필드(정의/관계/구현체)가 채워졌는지
  * critic_penalty: weak_related/opposite_concept 발견 시 하향

로그에 최소한 아래는 남기기:

* “왜 0.69인가?”를 분해한 항목별 기여도

---

## 10) 실험 매트릭스(하이퍼파라미터 탐색)

Hybrid의 성능은 주로 아래 변수에 좌우된다.

* Vector: topK ∈ {3, 5, 10}
* Graph: hop ∈ {1, 2, 3}
* Expansion relation filter:

  * allowlist: {ADDRESSES, IMPLEMENTS, PROPOSES, …}
* Rerank strategy:

  * (a) score-only
  * (b) critic penalty
  * (c) score + graph proximity 가중

실험 이름 예:

* `hyb_k5_h2_penalty`
* `hyb_k10_h3_scoreonly`

---

## 11) 의사결정 기준(“그래서 뭘 쓰나?”를 결론내는 규칙)

### 11.1 모드 선택 정책(운영)

* **Graph-only**: ID/명확한 엔티티/집계/경로 질의
* **Vector-only**: KG에 없거나 텍스트 스팬 기반 설명이 필요할 때
* **Hybrid**: 엔티티를 직접 말하지 않지만 KG 관계로 확장이 필요한 경우

### 11.2 Hybrid 도입의 합리화 조건

* (카테고리 “multi-hop / semantic+path”)에서

  * Hybrid Recall@K가 Vector-only 대비 유의미하게 높고
  * Precision 하락이 critic으로 제어 가능하며
  * latency 증가가 허용 범위(p95 기준) 내일 것

---

## 12) 바로 시작하는 최소 작업(MVP)

1. `eval/datasets/queries.yaml`에 **카테고리 30개**부터 구성

   * exact 8 / semantic 8 / multi-hop 8 / abstain 6 정도

2. `eval/runners/run_batch.py`로 **모드 강제 실행 + JSONL 로그** 남기기

3. `eval/metrics/retrieval_metrics.py`에서 Recall@K/Precision@K만 먼저 산출

4. 리포트에서 “Hybrid가 이긴 케이스/진 케이스” 10개씩 뽑아서

   * relevance critic이 필요한 패턴을 fp로 정리

---

## 부록) run_batch.py 의사코드(핵심 구조)

```python
for case in dataset:
    ctx = None
    if mode == "graph":
        ctx = graph_retriever.retrieve(case.query)
    elif mode == "vector":
        ctx = vector_retriever.retrieve(case.query, topk=K)
    elif mode == "hybrid":
        seeds = vector_retriever.retrieve(case.query, topk=K)
        expanded = graph_expander.expand(seeds.node_ids, hop=H)
        ctx = reranker.merge_and_rerank(seeds, expanded, critic=critic)

    answer, meta = synthesizer.generate(case.query, ctx)
    log_record = assemble_log(case, ctx, answer, meta)
    write_jsonl(log_record)
```

---

## 기대 산출물(Deliverables)

* `eval/datasets/queries.yaml`
* `runs/*.jsonl` (graph/vector/hybrid)
* `reports/efficacy_report.md` (카테고리별 성능 + 실패 사례)
* “모드 선택 정책” 초안 + hybrid 파라미터 추천값
