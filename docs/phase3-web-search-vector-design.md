# Phase 3: Web Search & Vector DB — Design Notes

> 구현 전 반드시 확인해야 할 사항을 정리한 문서.
> 현재 벡터 DB 구조의 문제점과, 웹 검색 결과 저장 시 따라야 할 원칙을 기술한다.

---

## 1. 현재 벡터 DB 구조의 문제점

### 현황
- `generate_embeddings.py`가 Neo4j 노드의 **개별 필드**(name, description)를 별도 문서로 임베딩
- `001_add_impl_descriptions.cypher`로 추가한 Implementation description은 **1~2문장** 수준
- ChromaDB entry ID: `"{node_id}:{field}"` (e.g. `m:react:description`)
- 메타데이터: `{node_id, node_label, field}` — 출처(source URL, 수집 시점) 없음

### 문제
1. **문서 단위가 아닌 필드 단위 저장**: 의미적으로 완결된 단위(chunk)가 아니라 DB 컬럼 값을 그대로 임베딩. "ReAct"라는 이름만 임베딩한 벡터는 검색에 거의 쓸모없음.
2. **텍스트가 너무 짧음**: 임베딩 모델은 일정 길이 이상의 맥락이 있어야 의미 벡터가 풍부해짐. 1~2문장은 sparse하고 discriminative하지 않음.
3. **출처 추적 불가**: 어떤 문서/URL에서 온 정보인지 메타데이터에 없음. 웹 검색 결과를 추가하면 더 심각해짐.
4. **중복/업데이트 전략 없음**: 같은 개념에 대해 웹에서 가져온 텍스트와 KG description이 별도 entry로 존재하게 됨. 충돌/중복 해소 전략이 없음.
5. **KG 관계 맥락 누락**: "ReAct ADDRESSES tool-use" 같은 관계 정보가 임베딩 텍스트에 포함되지 않아, 그래프 구조의 이점을 벡터 검색에서 활용 못함.

---

## 2. 벡터 DB 저장 원칙 (Web Search 결과 포함)

### 2.1 문서 단위 정의: Document → Chunk

관례적인 벡터 DB 파이프라인:

```
Raw Source (web page, PDF, paper)
    → Extract full text
    → Clean / normalize
    → Chunk (semantic or fixed-size with overlap)
    → Embed each chunk
    → Store with rich metadata
```

**우리 시스템에 적용:**

| 소스 | Raw 단위 | Chunk 전략 |
|------|---------|-----------|
| Web search result (Tavily) | 페이지 단위 text/snippet | Tavily의 `content` 필드가 이미 요약된 스니펫 → 그대로 하나의 chunk로 사용. `raw_content`가 있으면 paragraph 단위로 분할 |
| KG 노드 (기존) | 노드의 모든 텍스트 필드 | **필드별 분리 X** → 노드 당 하나의 통합 텍스트로 결합 후 임베딩 |
| 논문/아티클 (미래) | full text | 500~1000 token chunk, 100 token overlap |

### 2.2 통합 텍스트 생성 (KG 노드)

현재처럼 `name`, `description`을 개별 임베딩하지 말고, **노드 당 하나의 풍부한 텍스트**를 구성:

```
[Method] ReAct
Description: Interleaving reasoning traces and task-specific actions in LLM prompts...
Family: agent_loop_pattern
Addresses: Tool Use & Action (primary), Reasoning (secondary)
Implemented by: LangChain (core), LangGraph (first_class), ...
Seminal paper: Yao et al. 2022
```

이렇게 하면:
- 임베딩 벡터가 **관계 맥락**을 포함 → "tool use reasoning" 검색 시 ReAct가 높은 유사도
- 하나의 노드 = 하나의 chunk = 하나의 entry → 중복 없음
- ID: `kg:{node_id}` (e.g. `kg:m:react`)

### 2.3 필수 메타데이터

모든 벡터 DB entry에 반드시 포함:

```python
{
    # === Identity ===
    "source_type": "kg_node" | "web_search" | "paper" | "user_note",
    "source_id": str,         # kg node id OR URL OR doc id
    "source_url": str | None, # 원본 URL (웹 검색 시 필수)

    # === Provenance ===
    "collected_at": str,      # ISO timestamp — 언제 수집했는가
    "collector": str,         # "generate_embeddings.py" | "web_search_expander" | "user"

    # === KG Linkage ===
    "node_id": str | None,    # KG 노드와 연결된 경우 (웹 결과가 특정 노드와 관련될 때)
    "node_label": str | None, # "Method" | "Implementation" | ...

    # === Content ===
    "title": str,             # 표시용 제목
    "chunk_index": int,       # 같은 source에서 여러 chunk가 나올 때 순서
    "total_chunks": int,      # 해당 source의 총 chunk 수
}
```

### 2.4 ID 스키마

```
kg:{node_id}                    → KG 노드 통합 텍스트 (e.g. kg:m:react)
web:{url_hash}:{chunk_index}    → 웹 검색 결과 chunk
doc:{doc_id}:{chunk_index}      → 논문/아티클 chunk
```

기존 `{node_id}:{field}` 형식은 마이그레이션 시 제거.

### 2.5 중복/충돌 해소

- **같은 URL 재수집**: `web:{url_hash}:*` 기존 entries 삭제 후 재삽입 (upsert가 아닌 delete+insert)
- **KG 노드 재임베딩**: `kg:{node_id}` 단일 entry이므로 upsert로 덮어쓰기
- **웹 결과 → KG 승격**: 유저가 웹 검색 결과를 KG 노드로 승인하면, `web:*` entry를 삭제하고 `kg:*` entry로 교체

---

## 3. Web Search Expander 흐름

```
[expansion intent 또는 graph 결과 부족]
    │
    ▼
Tavily Search API (query, max_results=5)
    │
    ▼
결과 파싱: title, url, content, raw_content, score
    │
    ├─→ 각 result를 chunk화 → 임베딩 → ChromaDB 저장
    │     metadata: source_type="web_search", source_url=url, collected_at=now
    │
    └─→ Synthesizer에 웹 결과 전달 → 답변 생성
          답변에 "[출처: URL]" 명시
```

### Tavily API 참고

```python
from tavily import TavilyClient

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
response = client.search(
    query="ReAct prompting framework",
    max_results=5,
    include_raw_content=False,  # True면 전체 페이지 텍스트 (긴 문서)
    search_depth="basic",       # "basic" | "advanced"
)
# response["results"]: list of {title, url, content, score, raw_content?}
```

- `content`: Tavily가 요약한 스니펫 (~200-500 words) → 바로 하나의 chunk로 사용 가능
- `raw_content`: 전체 페이지 텍스트 → 긴 경우 chunking 필요
- 기본적으로 `include_raw_content=False`로 시작, 필요 시 `True`

---

## 4. 마이그레이션 계획 (기존 벡터 DB)

### Step 1: `generate_embeddings.py` 리팩터링
- 필드별 개별 임베딩 → **노드 당 통합 텍스트** 생성 후 단일 임베딩
- 통합 텍스트에 관계 맥락 포함 (ADDRESSES, IMPLEMENTS 등)
- 메타데이터 스키마를 2.3 기준으로 확장
- ID를 `kg:{node_id}` 형식으로 변경

### Step 2: ChromaDB collection 재생성
- 기존 `kg_nodes` collection 삭제 후 재생성 (ID 스키마 변경으로 upsert 불가)
- 또는 새 collection `kg_v2`를 만들고 코드가 이를 가리키도록 전환

### Step 3: `vector_store.py` 메타데이터 필터링 지원
- `source_type` 기반 필터: KG 결과만, 웹 결과만, 또는 전체
- ChromaDB `where` 필터: `{"source_type": "web_search"}`

---

## 5. 구현 시 주의사항

1. **Tavily API 키**: `.env`의 `TAVILY_API_KEY` 사용. `config/settings.py`에 추가 필요.
2. **임베딩 모델 일관성**: 웹 검색 결과와 KG 노드가 **동일한 임베딩 모델**(`text-embedding-3-small`)을 사용해야 유사도 비교가 유의미.
3. **Rate limit**: Tavily free tier는 1,000 req/month. 테스트 시 캐싱 고려.
4. **웹 결과 품질**: Tavily score가 낮은 결과는 필터링 (threshold 설정).
5. **KG 승격은 Phase 3.2 (유저 승인 UI)**: 이번 단계에서는 웹 결과를 벡터 DB에 저장하고 답변에 활용하는 것까지만. KG 노드 추가는 유저 승인 후.
6. **Collection 분리 vs 통합**: 하나의 collection에 `source_type` 메타데이터로 구분하는 것을 권장. 검색 시 cross-source relevance를 자연스럽게 비교 가능.

---

## 6. 체크리스트 (구현 시작 전 확인)

- [ ] `generate_embeddings.py` 리팩터: 노드 통합 텍스트 + 관계 맥락 포함
- [ ] 메타데이터 스키마 확장 (`source_type`, `source_url`, `collected_at`, ...)
- [ ] ID 스키마 변경 (`kg:{node_id}`, `web:{hash}:{chunk}`)
- [ ] ChromaDB collection 마이그레이션
- [ ] `vector_store.py`에 메타데이터 필터링 추가
- [ ] `config/settings.py`에 `TAVILY_API_KEY` 추가
- [ ] `pyproject.toml`에 `tavily-python` 추가
- [ ] Web Search Expander 노드 구현
- [ ] Synthesizer에 웹 출처 표시 로직 추가
- [ ] 기존 `vector_first`/`hybrid` 검색이 새 스키마에서도 동작하는지 검증

---

### FYI (다른 세션에서 작업 중 로그 전달용)

● Read 1 file (ctrl+o to expand)
                                                                                                                        
● This is the old Streamlit plan — completely different task. I need to explore the current codebase to understand what   needs to change for the vector DB preparation work.
                                                                                                                        
● 2 Explore agents finished (ctrl+o to expand)
   ├─ Explore KG node text fields · 7 tool uses · 51.4k tokens                                                             
   │  ⎿  Done                                                                                                              
   └─ Explore vector/retrieval pipeline · 9 tool uses · 32.9k tokens
       ⎿  Done

● Now let me design the implementation plan based on these findings.