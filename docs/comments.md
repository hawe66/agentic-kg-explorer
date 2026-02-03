CHANGELOG.md를 보니 프로젝트가 상당히 많이 진행되었네요! 피드백 포인트들을 정리하고 해결 방향을 제안해드리겠습니다.

---

## 문제 정리 및 해결 방향

### 1. Critic: 데이터 충분성 판단 부재

**문제:** Critic이 검색 결과가 질문에 답하기에 충분한지 판단하지 못함.

**해결 방향:**
```python
# src/agents/nodes/critic.py (신규)
def evaluate_sufficiency(query: str, intent: str, results: dict) -> dict:
    """검색 결과가 질문에 충분한지 평가"""
    
    checks = {
        "has_results": bool(results.get("kg_results") or results.get("vector_results")),
        "entity_coverage": check_entity_coverage(query, results),  # 질문의 엔티티가 결과에 있는가
        "intent_fulfillment": check_intent_fulfillment(intent, results),  # comparison인데 1개만?
        "semantic_relevance": check_semantic_relevance(query, results),  # vector score 기반
    }
    
    is_sufficient = all(checks.values())
    
    return {
        "is_sufficient": is_sufficient,
        "checks": checks,
        "recommendation": "proceed" if is_sufficient else "expand_search" or "out_of_scope"
    }
```

파이프라인에 Critic 노드 추가:
```
retrieve_from_graph → critic_evaluate → [sufficient?] → synthesize / web_search
```

---

### 2. Intent 분류 체계 빈약

**문제:** lookup, path, comparison, expansion 4개로는 다양한 질문 커버 불가.

**해결 방향:**

```python
# config/intents.yaml (신규)
intents:
  # 읽기
  lookup:
    description: "특정 엔티티 조회"
    examples: ["ReAct가 뭐야?", "m:react의 maturity는?"]
  exploration:
    description: "관계 탐색 (1-hop)"
    examples: ["Memory 관련 Method는?"]
  path_trace:
    description: "경로 추적 (multi-hop)"
    examples: ["CoT에서 LangChain까지 어떻게 연결돼?"]
  aggregation:
    description: "집계/통계"
    examples: ["Principle별 Method 수", "production Method 몇 개?"]
  
  # 분석
  comparison:
    description: "엔티티 비교"
    examples: ["LangChain vs CrewAI", "Planning과 Reasoning 차이"]
  recommendation:
    description: "조건 기반 추천"
    examples: ["Reasoning 개선할 Method 추천해줘"]
  coverage_check:
    description: "KG 품질/갭 분석"
    examples: ["Paper 없는 Method 목록"]
  
  # 메타
  definition:
    description: "스키마/구조 설명"
    examples: ["ADDRESSES 관계가 뭐야?"]
  
  # 쓰기
  update:
    description: "데이터 추가/수정 제안"
    examples: ["m:self-rag 추가해줘"]
  
  # 외부
  expansion:
    description: "도메인 내지만 웹 검색 필요"
    examples: ["최신 MCP 변경사항"]
  out_of_scope:
    description: "도메인 무관"
    examples: ["오늘 날씨", "Why do we live?"]
```

---

### 3. Search Planner 하드코딩

**문제:** Cypher 템플릿과 경로 방향이 코드에 고정됨.

**해결 방향:**

```yaml
# config/cypher_templates.yaml (신규)
templates:
  lookup_principle:
    intent: lookup
    entity_types: [Principle]
    cypher: |
      MATCH (p:Principle)
      WHERE toLower(p.name) CONTAINS toLower($entity) OR p.id = $entity
      OPTIONAL MATCH (m:Method)-[a:ADDRESSES]->(p)
      RETURN p, collect({method: m, role: a.role}) as methods
      
  lookup_method:
    intent: lookup
    entity_types: [Method]
    cypher: |
      MATCH (m:Method)
      WHERE toLower(m.name) CONTAINS toLower($entity) OR m.id = $entity
      OPTIONAL MATCH (m)-[a:ADDRESSES]->(p:Principle)
      OPTIONAL MATCH (i:Implementation)-[impl:IMPLEMENTS]->(m)
      RETURN m, collect(DISTINCT p) as principles, collect(DISTINCT i) as implementations
      
  comparison_principle:
    intent: comparison
    entity_types: [Principle, Principle]
    cypher: |
      MATCH (p1:Principle), (p2:Principle)
      WHERE (toLower(p1.name) CONTAINS toLower($entity1) OR p1.id = $entity1)
        AND (toLower(p2.name) CONTAINS toLower($entity2) OR p2.id = $entity2)
      OPTIONAL MATCH (m1:Method)-[:ADDRESSES]->(p1)
      OPTIONAL MATCH (m2:Method)-[:ADDRESSES]->(p2)
      OPTIONAL MATCH (m1)-[:ADDRESSES]->(p2)  // 교집합
      RETURN p1, p2, collect(DISTINCT m1) as methods1, collect(DISTINCT m2) as methods2

  aggregation_by_principle:
    intent: aggregation
    cypher: |
      MATCH (p:Principle)<-[:ADDRESSES]-(m:Method)
      RETURN p.name, count(m) as method_count
      ORDER BY method_count DESC

  multi_hop_path:
    intent: path_trace
    cypher: |
      MATCH path = (start)-[*1..3]-(end)
      WHERE start.id = $start_id AND end.id = $end_id
      RETURN path
```

Search Planner가 YAML에서 템플릿 로드:
```python
def select_template(intent: str, entity_types: list[str]) -> dict:
    templates = load_yaml("config/cypher_templates.yaml")
    for t in templates:
        if t["intent"] == intent and matches_entity_types(t, entity_types):
            return t
    return None
```

---

### 4. Intent 프롬프트에 KG 엔티티 정보 부재

**문제:** LLM이 실제 KG에 어떤 엔티티가 있는지 모름.

**해결 방향:**

```python
# scripts/generate_entity_catalog.py (신규)
def generate_entity_catalog():
    """Neo4j에서 엔티티 목록 추출하여 캐시"""
    
    with Neo4jClient() as client:
        principles = client.query("MATCH (p:Principle) RETURN p.name, p.id")
        methods = client.query("MATCH (m:Method) RETURN m.name, m.id, m.aliases")
        implementations = client.query("MATCH (i:Implementation) RETURN i.name, i.id, i.aliases")
        standards = client.query("MATCH (s:Standard) RETURN s.name, s.id")
    
    catalog = {
        "principles": [{"name": p["name"], "id": p["id"]} for p in principles],
        "methods": [...],
        "implementations": [...],
        "standards": [...],
        "aliases": build_alias_map(methods, implementations),  # CoT → m:cot
        "generated_at": datetime.now().isoformat()
    }
    
    with open("data/entity_catalog.json", "w") as f:
        json.dump(catalog, f)
    
    return catalog
```

Intent Classifier 프롬프트에 주입:
```python
ENTITY_CATALOG = load_json("data/entity_catalog.json")

INTENT_PROMPT = f"""
You are classifying queries for an Agentic AI knowledge graph.

Known entities:
- Principles: {', '.join(p['name'] for p in ENTITY_CATALOG['principles'])}
- Methods (examples): {', '.join(m['name'] for m in ENTITY_CATALOG['methods'][:15])}...
- Implementations: {', '.join(i['name'] for i in ENTITY_CATALOG['implementations'])}

Aliases: CoT=Chain-of-Thought, RAG=Retrieval-Augmented Generation, ...

Extract entities using EXACT names from the list above.
...
"""
```

---

### 5. Cypher 쿼리 제한적 (프로젝트 목표: 지식 그래프 구축)

**문제:** 챗봇이 아니라 좋은 지식 그래프를 만드는 게 목표인데, 현재 Cypher가 너무 단순함.

**해결 방향:**

지식 그래프 관리/분석용 Cypher 추가:
```yaml
# config/cypher_templates.yaml에 KG 관리용 템플릿 추가

# 품질 분석
coverage_methods_without_paper:
  intent: coverage_check
  description: "논문 연결 없는 Method"
  cypher: |
    MATCH (m:Method)
    WHERE NOT (m)<-[:PROPOSES]-(:Document) AND m.seminal_source IS NULL
    RETURN m.id, m.name, m.year_introduced
    ORDER BY m.year_introduced DESC

coverage_orphan_implementations:
  intent: coverage_check
  description: "Method 연결 없는 Implementation"
  cypher: |
    MATCH (i:Implementation)
    WHERE NOT (i)-[:IMPLEMENTS]->(:Method)
    RETURN i.id, i.name

coverage_principle_distribution:
  intent: aggregation
  description: "Principle별 Method/Implementation 분포"
  cypher: |
    MATCH (p:Principle)
    OPTIONAL MATCH (m:Method)-[:ADDRESSES]->(p)
    OPTIONAL MATCH (i:Implementation)-[:IMPLEMENTS]->(m)
    RETURN p.name, 
           count(DISTINCT m) as method_count,
           count(DISTINCT i) as impl_count
    ORDER BY method_count DESC

# 경로 분석
full_path_principle_to_standard:
  intent: path_trace
  description: "Principle → Method → Implementation → Standard 전체 경로"
  cypher: |
    MATCH path = (p:Principle)<-[:ADDRESSES]-(m:Method)
                 <-[:IMPLEMENTS]-(i:Implementation)
                 -[:COMPLIES_WITH]->(sv:StandardVersion)
    WHERE p.id = $principle_id
    RETURN path
```

---

### 6. Confidence 계산 근본 재설계

**문제:** 결과 수 기반 confidence는 완전히 잘못됨.

**해결 방향:**

```python
# src/agents/nodes/synthesizer.py

def calculate_confidence(
    query: str,
    intent: str,
    entities: list[str],
    kg_results: list,
    vector_results: list
) -> float:
    """다차원 confidence 계산"""
    
    if not kg_results and not vector_results:
        return 0.0
    
    scores = []
    
    # 1. 엔티티 매칭 (0.0 - 1.0)
    # 질문에서 추출한 엔티티가 결과에 있는가?
    matched = sum(1 for e in entities if entity_in_results(e, kg_results))
    entity_score = matched / len(entities) if entities else 0.5
    scores.append(("entity_match", entity_score, 0.3))
    
    # 2. Intent 충족도 (0.0 - 1.0)
    # comparison인데 결과가 1개? lookup인데 정확 매칭?
    intent_score = calculate_intent_fulfillment(intent, kg_results, vector_results)
    scores.append(("intent_fulfillment", intent_score, 0.3))
    
    # 3. 데이터 완성도 (0.0 - 1.0)
    # description, seminal_source 등 핵심 필드 채워짐 비율
    completeness = calculate_completeness(kg_results)
    scores.append(("completeness", completeness, 0.2))
    
    # 4. Vector 유사도 (0.0 - 1.0)
    if vector_results:
        avg_vector_score = sum(r["score"] for r in vector_results) / len(vector_results)
        scores.append(("vector_similarity", avg_vector_score, 0.2))
    else:
        scores.append(("vector_similarity", 0.5, 0.2))  # neutral
    
    # 가중 평균
    total = sum(score * weight for _, score, weight in scores)
    
    return round(total, 2)
```

---

### 7. LangChain Docs 크롤링 스크립트

**문제:** LangChain docs를 data/papers에 넣고 싶음. 범용 크롤러 필요.

**해결 방향:**

```python
# scripts/crawl_docs.py (신규)

"""
범용 문서 크롤러.

Usage:
  poetry run python scripts/crawl_docs.py --url "https://python.langchain.com/docs" --output data/papers/langchain
  poetry run python scripts/crawl_docs.py --sitemap "https://example.com/sitemap.xml" --output data/papers/example
  poetry run python scripts/crawl_docs.py --urls-file urls.txt --output data/papers/custom
"""

import argparse
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

def crawl_page(url: str, client: httpx.Client) -> dict:
    """단일 페이지 크롤링"""
    resp = client.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 메인 콘텐츠 추출 (사이트별 selector 조정 가능)
    content = soup.select_one("main, article, .content, .markdown-body")
    if not content:
        content = soup.body
    
    # Markdown 변환
    md = markdownify(str(content), heading_style="ATX")
    
    return {
        "url": url,
        "title": soup.title.string if soup.title else url,
        "content_md": md,
        "crawled_at": datetime.now().isoformat()
    }

def crawl_site(base_url: str, output_dir: Path, max_pages: int = 100):
    """사이트 크롤링 (링크 따라가기)"""
    visited = set()
    queue = [base_url]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            
            try:
                page = crawl_page(url, client)
                visited.add(url)
                
                # 파일 저장
                filename = hashlib.md5(url.encode()).hexdigest()[:12] + ".md"
                filepath = output_dir / filename
                
                with open(filepath, "w") as f:
                    f.write(f"---\n")
                    f.write(f"source_url: {url}\n")
                    f.write(f"title: {page['title']}\n")
                    f.write(f"crawled_at: {page['crawled_at']}\n")
                    f.write(f"---\n\n")
                    f.write(page["content_md"])
                
                # 링크 추출 (같은 도메인만)
                soup = BeautifulSoup(page["content_md"], "html.parser")
                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])
                    if urlparse(link).netloc == urlparse(base_url).netloc:
                        if link not in visited:
                            queue.append(link)
                
                print(f"[{len(visited)}/{max_pages}] {url}")
                
            except Exception as e:
                print(f"Error crawling {url}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Base URL to crawl")
    parser.add_argument("--sitemap", help="Sitemap XML URL")
    parser.add_argument("--urls-file", help="File with URLs (one per line)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    
    if args.url:
        crawl_site(args.url, Path(args.output), args.max_pages)
    elif args.sitemap:
        crawl_from_sitemap(args.sitemap, Path(args.output))
    elif args.urls_file:
        crawl_from_file(args.urls_file, Path(args.output))
```

---

### 8. Streamlit UI 개선

**문제들:**
- Example query 클릭 시 agent가 응답 안 함
- Web result 폰트 너무 큼
- KG 추가 UI가 스크롤 맨 위에 있어서 불편
- Local docs 업로드 UI 없음

**해결 방향:**

```python
# streamlit_app.py 개선 사항

# 1. Example query 클릭 → 자동 실행
if st.button("What is ReAct?", key="example_react"):
    st.session_state.query = "What is ReAct?"
    st.session_state.auto_submit = True

if st.session_state.get("auto_submit"):
    run_query(st.session_state.query)
    st.session_state.auto_submit = False

# 2. Web result 폰트 크기 조정
st.markdown("""
<style>
.web-result { font-size: 0.9rem; }
.web-result-title { font-size: 1rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. KG 추가 UI를 Floating Panel로
with st.sidebar:
    st.header("Add to Knowledge Graph")
    # 또는 modal dialog 사용

# 또는 expander를 chat 하단에 고정
with st.expander("📥 Add to Knowledge Graph", expanded=False):
    selected_results = st.multiselect("Select results to add", options=...)
    if st.button("Add Selected"):
        add_to_kg(selected_results)

# 4. Local docs 업로드 UI
st.sidebar.header("📄 Upload Documents")
uploaded_files = st.sidebar.file_uploader(
    "Upload papers/docs (PDF, MD, TXT)",
    accept_multiple_files=True,
    type=["pdf", "md", "txt"]
)

if uploaded_files:
    for file in uploaded_files:
        save_path = Path("data/papers") / file.name
        save_path.write_bytes(file.read())
        st.sidebar.success(f"Saved: {file.name}")
    
    if st.sidebar.button("Process & Embed"):
        process_uploaded_docs(uploaded_files)
```

---

### 9. 새 Document를 KG에 자동 연결

**문제:** 새로 추가된 문서가 Principle/Method/Implementation과 자동 연결되지 않음.

**해결 방향:**

```python
# src/agents/nodes/document_linker.py (신규)

def link_document_to_kg(doc_id: str, doc_content: str) -> list[dict]:
    """문서 내용 분석하여 KG 엔티티와 연결"""
    
    # 1. 문서 임베딩
    doc_embedding = embed(doc_content)
    
    # 2. 유사 Method/Implementation 검색
    similar_nodes = vector_store.query(doc_embedding, top_k=10)
    
    # 3. LLM으로 관계 추론
    prompt = f"""
    Document content (excerpt):
    {doc_content[:2000]}
    
    Similar nodes found:
    {format_nodes(similar_nodes)}
    
    Determine relationships:
    - Does this document PROPOSE a new Method? If so, which one?
    - Does it EXTEND or VARIANT_OF an existing Method?
    - Does it EVALUATE any Methods/Implementations?
    
    Return JSON:
    {{
      "proposes": ["method_name"],
      "extends": {{"new": "method_name", "base": "existing_method_id"}},
      "evaluates": ["method_id1", "impl_id2"]
    }}
    """
    
    relationships = llm.generate(prompt)
    
    # 4. 사용자 승인 대기열에 추가
    pending_links = []
    for rel_type, targets in relationships.items():
        for target in targets:
            pending_links.append({
                "document_id": doc_id,
                "relationship": rel_type,
                "target": target,
                "confidence": calculate_link_confidence(...),
                "status": "pending_approval"
            })
    
    return pending_links
```

워크플로우:
```
문서 업로드 → 임베딩 + KG 유사도 검색 → LLM 관계 추론 
    → Pending Queue에 저장 → UI에서 승인/거절 → Neo4j에 관계 생성
```

---

## 우선순위 정리

### P0 (즉시) ✅ DONE
- [x] Confidence 계산 재설계 → Multi-dimensional (entity/intent/completeness/vector)
- [x] `out_of_scope` intent 추가 → 5 intents now (+ out_of_scope)
- [x] Entity Catalog 생성 + 프롬프트 주입 → `scripts/generate_entity_catalog.py`

### P1 (단기) ✅ DONE
- [x] Intent 분류 체계 확장 (YAML 기반) → `config/intents.yaml` (11 intents)
- [x] Cypher 템플릿 외부화 (YAML) → `config/cypher_templates.yaml` (20+ templates)
- [ ] ~~Critic 노드 추가 (데이터 충분성 판단)~~ → Moved to Phase 4
- [x] Streamlit UI 개선 (example 자동실행, 폰트, floating panel)

### P2 (중기)
- [ ] 범용 문서 크롤러 스크립트
- [ ] Local docs 업로드 UI
- [ ] Document → KG 자동 연결 (link_document_to_kg)
- [x] ~~KG 관리용 Cypher (coverage_check, aggregation)~~ → Included in cypher_templates.yaml
- [x] ~~Graph visualization~~ → `streamlit-agraph` in `src/ui/app.py` (toggle, node colors, overview mode)

### Phase 4 (Critic Agent)
- [ ] EvaluationCriteria nodes derived from Principles
- [ ] Evaluation logic with multi-dimensional scoring
- [ ] Guideline versioning
- [ ] Human-in-the-loop approval gates

추가 질문이나 특정 항목 더 상세하게 보고 싶으시면 말씀해주세요!