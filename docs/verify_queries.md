**약점(의도–행동 불일치, relevance 비판 부재, “데이터 없음” 처리, confidence 불투명)**이 **반드시 드러나도록** 설계한 카테고리별 “검증용 쿼리 세트”

아래는 단순 질문 목록이 아니라, **각 질문으로 무엇을 검증해야 하는지(로그/출력 관찰 포인트)**까지 함께 붙였습니다.
(당신 출력 포맷: `intent / entities / confidence / sources / vector_results / cypher_executed / kg_results` 기준)

---

# 0) 공통 체크리스트 (모든 쿼리에 적용)

각 쿼리를 던지고 아래를 같이 기록하면 “어디가 문제인지”가 바로 보입니다.

1. **Intent–행동 일치**

* intent가 `expansion`인데도 **vector+KG만으로 답을 “완성된 것처럼”** 내면 → 지금 문제 재현
* 반대로 intent가 `lookup/path/aggregation`인데 vector만 돌고 cypher가 안 돌면 → 라우팅 문제

2. **Relevance 비판(가장 중요)**

* vector hit가 “관련 약함/반대 개념”이면 Synthesizer가:

  * **(a) 반대 개념임을 명시**하거나
  * **(b) ‘직접 매칭 없음’ 선언 + 추가 질문(clarify)**
    해야 통과

3. **데이터 충분성 판단**

* KG에 없거나 수치 데이터 없는 질문에서:

  * “없다/모른다”를 말하는지
  * 근거 없이 “대충 비교/수치”를 만들지 않는지

4. **Confidence의 일관성/설명 가능성**

* direct ID 조회는 confidence 높아야 하고
* 애매한 vector hit(0.6대)로 때우면 confidence 낮아야 정상
* confidence 산정 근거를 답변/메타로 설명 가능해야 함

---

# 1) 빠른 회귀 테스트(15개) — 매 빌드마다 돌리기

> 목적: 파이프라인이 깨졌는지 / relevance-critic이 개선됐는지 빠르게 확인

1. **`m:icl` 설명해줘**

   * 기대: CY(직접 KG), confidence ↑

2. **In-Context Learning은 어떤 Principle을 address해?**

   * 기대: V+KG 또는 CY, `p:learning` 연결

3. **`impl:zep`의 라이선스는?**

   * 기대: CY, `Apache-2.0`(KG 기준)

4. **Zep은 어떤 Method를 implements 해?**

   * 기대: CY(impl→method), `m:temporal-kg-memory`

5. **Temporal KG Memory는 어떤 Principle을 address해?**

   * 기대: CY, `p:memory`

6. **`doc:rag-2020`에서 제안한 Method는?**

   * 기대: CY(doc→method), `m:rag`

7. **RAG는 ‘parametric/non-parametric memory’를 어떻게 결합해?**

   * 기대: doc 근거 인용 + 설명(단, “parameter-based learning”으로 비약 금지)

8. **parameter based learning이 뭐야? (KG 기반으로만)**

   * 기대: ABSTAIN + clarify (혹은 관련 개념 제시하되 “직접 일치 없음/반대 개념 가능” 명시)

9. **ICL은 parameter를 업데이트 하는 학습이야?**

   * 기대: “아님(비모수적/컨텍스트 기반)” 명확히

10. **RLHF를 ‘parameter based learning’ 예시로 드는 게 타당해?**

* 기대: 비판적으로 평가(“학습은 parameter 업데이트지만 질문 의도와 다를 수 있음” 같은 식)

11. **Planning과 Reasoning의 차이가 뭐야?**

* 기대: “KG에 해당 노드 없음” + (가능하면 일반 설명)
* **중요:** Implementation compare cypher를 실행하면 실패(현재 버그 재현)

12. **ICL과 RLHF 비교해줘**

* 기대: “Method 비교” 라우트 필요
* 현재 impl compare로 가면 실패(개선 목표)

13. **maturity가 production인 Method 목록**

* 기대: aggregation/filter 의도 + cypher

14. **p:memory를 address하는 Method와 그 구현체를 알려줘**

* 기대: 2-hop (Principle→Method→Implementation)

15. **이번 답변 confidence는 어떤 근거로 계산했어?**

* 기대: 메타 설명(최소한 “direct match/score/근거 수/충돌 여부” 등)

---

# 2) Intent 분류 경계 테스트 (8개)

> 목적: “comparison/expansion/lookup/path/aggregation” 경계에서 잘못된 cypher가 도는지 확인

1. **Planning과 Reasoning의 차이 뭐야?**

   * 기대: 개념 비교(Principle/Capability 비교) / **impl compare cypher 금지**

2. **Method와 Implementation의 차이가 뭐야? (너의 KG 스키마 기준)**

   * 기대: 스키마 설명 + KG 타입 참조

3. **ReAct는 어떤 Principle을 address해?**

   * 기대: path(lookup+relation)

4. **RAG는 어떤 Principle을 address해?**

   * 기대: path(없으면 “연결 없음”)

5. **Zep과 MemGPT 비교해줘**

   * 기대: comparison
   * MemGPT가 KG에 없으면 “없다” + web 제안(가능하면)

6. **Agentic AI에서 “parameter based learning”은 어디에 해당해?**

   * 기대: expansion + (직접 매칭 없음) + 정의 재확인 질문

7. **가장 많은 Method를 구현하는 Implementation은?**

   * 기대: aggregation

8. **2020년에 등장한 Method만 보여줘**

   * 기대: filter(temporal) + cypher

---

# 3) Vector vs Cypher 역할 분담 테스트 (8개)

> 목적: direct ID는 cypher 우선, 서술형/오타/한국어는 vector→KG enrichment가 동작하는지

1. **`m:icl`**

   * 기대: CY (vector 불필요)

2. **`impl:zep`**

   * 기대: CY

3. **`doc:rag-2020`**

   * 기대: CY

4. **시간적 지식 그래프 기반 메모리 아키텍처가 뭐야?**

   * 기대: V(한국어 desc hit) → KG enrichment → p:memory/impl:zep 연결

5. **Graphiti가 뭐야?** (alias 테스트)

   * 기대: V→KG, `m:temporal-kg-memory`로 resolve

6. **Reinforcement Learning from Human Feedback 설명해줘**

   * 기대: V(영문 alias)→KG, `m:rlhf`

7. **few-shot learning은 KG에서 뭐로 저장돼 있어?**

   * 기대: V→KG, `m:icl`

8. **retrieve-then-generate 방식의 방법론 알려줘**

   * 기대: V(키워드)→KG, `m:rag`

---

# 4) Synthesizer “비판적 관련성 평가” 테스트 (10개)

> 목적: 지금 핵심 문제(약한/반대 매칭을 “관련있다”로 포장)를 재현시키고, 개선됐는지 확인

1. **parameter based learning**

   * 기대: “직접 없음” + “ICL은 non-parametric(반대)”를 명시 + clarify

2. **non-parametric learning의 예시를 KG에서 2개만 들어줘**

   * 기대: ICL은 OK / RLHF는 제외(또는 “학습 파라미터 업데이트라서 반대” 명시)

3. **ICL을 ‘parameter based learning’ 예시로 드는 건 왜 부적절해?**

   * 기대: 반대 개념 논리 제시

4. **RAG 논문에서 말하는 ‘parametric memory’가 뭔지 KG 근거로만 설명해줘**

   * 기대: doc 문장 인용/요약 + “이게 곧 parameter-based learning은 아님” 경계

5. **RLHF가 “parameter based learning”과 관련이 있다고 말할 수 있어? 단, 어떤 의미에서만?**

   * 기대: “모델 파라미터 업데이트” 관점에서는 관련 가능, 하지만 질문 의도와 다를 수 있음

6. **Temporal KG Memory는 파라미터 업데이트를 통해 학습해?**

   * 기대: “메모리 아키텍처/서비스”로서 별개(학습=training과 구분)

7. **Zep은 RLHF를 implements해?**

   * 기대: 아니오(근거 기반)

8. **‘parameter based learning’을 검색했는데 score 0.65대 결과만 나왔다면 답을 어떻게 해야 해?**

   * 기대: ABSTAIN/clarify 정책 설명(“관련성 낮아 확정 불가”)

9. **MemGPT와 Zep의 벤치마크 성능 비교해줘(수치 포함)**

   * 기대: “수치 데이터 없음” 선언 + 어떤 데이터가 필요하다고 말하기

10. **RAG 2020 논문의 실험 결과(EM/F1)를 알려줘**

* 기대: KG에 수치 없으면 “없다”(환각 금지)

---

# 5) KG 멀티홉/경로 추론 테스트 (8개)

> 목적: vector→KG enrichment가 “연결을 가져오긴 하는데” 답으로 제대로 쓰는지, 그리고 2~3 hop이 가능한지

1. **p:memory를 address하는 Method를 implement하는 Implementation은?**

   * 기대: 2-hop

2. **impl:zep이 implement하는 method가 address하는 principle을 모두 보여줘**

   * 기대: 2-hop (impl→method→principle)

3. **doc:rag-2020이 propose한 method의 maturity는?**

   * 기대: doc→method→property

4. **m:rag의 seminal_source(원 논문) url 알려줘**

   * 기대: method→doc url

5. **m:icl과 m:rlhf가 공통으로 address하는 principle은?**

   * 기대: `p:learning`

6. **m:temporal-kg-memory와 m:rag는 각각 어떤 principle을 address해? 차이 중심으로**

   * 기대: 양쪽 연결 비교(없으면 “연결 없음”)

7. **knowledge-graph 태그가 있는 method와 그 구현체**

   * 기대: tag filter + hop

8. **maturity=production 인 method 중 p:memory를 address하는 것만**

   * 기대: filter + hop

---

# 6) Aggregation / Ranking / Filtering 테스트 (6개)

> 목적: “aggregation intent가 없어서 어디로 분류?” 문제를 강제로 드러냄

1. **Implementation이 가장 많이 implements 하는 Method TOP 3는?**
2. **Principle별로 address하는 Method 개수 랭킹 TOP 5**
3. **maturity별(Method) 개수 집계해줘**
4. **tags에 memory가 포함된 Implementation 목록**
5. **year_introduced가 2020인 Method 목록**
6. **(가능하면) method_family별로 method 수 집계**

* 기대: cypher에 `COUNT`, `ORDER BY`, `GROUP BY(=WITH ...)`가 들어가야 정상

---

# 7) Entity resolution / 한국어·영어·오타 테스트 (8개)

> 목적: entities 추출 + alias + 오타에 대한 vector 견고성 확인

1. **인간 피드백을 통한 강화학습 정렬 기법이 뭐야?** (→ RLHF)
2. **ZEP 메모리 서비스 설명해줘** (→ Zep)
3. **In context learnig 설명해줘** (오타)
4. **retrievel augmented generation이 뭐야?** (오타)
5. **RAG(2005.11401) 설명해줘** (id/번호 기반)
6. **컨텍스트 내 예시 학습 기법 알려줘** (→ ICL)
7. **시간적 KG 메모리(Graphiti)와 Zep의 관계는?** (alias+impl 연결)
8. **“비모수적(non-parametric)”이 포함된 method만** (키워드)

---

# 8) Confidence 검증 테스트 (6개)

> 목적: confidence가 “근거/매칭 강도/충돌”을 반영하는지 확인

1. **m:icl**

   * 기대: confidence 매우 높음(직접 매칭)

2. **impl:zep 라이선스/maintainer/플랫폼 한 번에**

   * 기대: confidence 높음(모두 KG 속성)

3. **parameter based learning**

   * 기대: confidence 낮음 + “직접 없음” + clarify

4. **Graphiti**

   * 기대: confidence 중~높(별칭 매핑 성공 시)

5. **LangChain의 최신 버전은?**

   * 기대: confidence 낮음 + “release 데이터 없음/웹 필요”
   * (웹 모듈 없으면 “모름”이 정답)

6. **이번 답변 confidence를 score/근거 수/일치 여부로 분해해서 설명해줘**

   * 기대: **불투명성 문제(0.69)**를 직접 검증

---

# 9) (선택) “정책/가드레일” 준수 테스트 (추가 6개)

> 목적: Synthesizer가 “답변 포장”을 멈추고, 정책대로 제한/거절/추가질문을 하는지

1. **KG 근거가 없으면 ‘없다’고 말해줘. parameter based learning 정의해줘**
2. **vector score 0.68 미만 결과는 무시하고 답해줘: parameter based learning**
3. **근거 없는 추측은 하지 말고, 필요한 추가 질문 2개만 해줘: Planning vs Reasoning**
4. **너의 sources에 포함된 것만 인용해서 답해줘: RAG의 parametric/non-parametric**
5. **관련 노드가 없으면 web search가 필요하다고 말해줘: OpenAI Agents SDK 출시일**
6. **‘관련이 약한데 억지로 엮는다’고 판단되면 그 이유를 1문장으로 써줘: ICL vs parameter based learning**

---

# 10) (보너스) 자동 테스트용 JSON 샘플 (핵심 20개만)

원하시면 이 형태로 50~100개까지 확장해서 “회귀 테스트 데이터셋”으로 만들어드릴 수 있어요.

```json
[
  {"id":"S01","category":"direct-id","query":"m:icl 설명해줘"},
  {"id":"S02","category":"path","query":"In-Context Learning은 어떤 Principle을 address해?"},
  {"id":"S03","category":"direct-id","query":"impl:zep의 라이선스는?"},
  {"id":"S04","category":"path","query":"Zep은 어떤 Method를 implements 해?"},
  {"id":"S05","category":"path","query":"Temporal KG Memory는 어떤 Principle을 address해?"},
  {"id":"S06","category":"doc-path","query":"doc:rag-2020에서 제안한 Method는?"},
  {"id":"S07","category":"relevance","query":"parameter based learning이 뭐야? (KG 기반으로만)"},
  {"id":"S08","category":"relevance","query":"ICL을 parameter based learning 예시로 드는 게 타당해?"},
  {"id":"S09","category":"comparison-boundary","query":"Planning과 Reasoning의 차이가 뭐야?"},
  {"id":"S10","category":"comparison-methods","query":"ICL과 RLHF 비교해줘"},
  {"id":"S11","category":"aggregation","query":"maturity가 production인 Method 목록"},
  {"id":"S12","category":"multi-hop","query":"p:memory를 address하는 Method와 그 구현체를 알려줘"},
  {"id":"S13","category":"alias","query":"Graphiti가 뭐야?"},
  {"id":"S14","category":"bilingual","query":"인간 피드백을 통한 강화학습 정렬 기법이 뭐야?"},
  {"id":"S15","category":"abstain","query":"MemGPT와 Zep의 벤치마크 성능 비교해줘(수치 포함)"},
  {"id":"S16","category":"abstain","query":"RAG 2020 논문의 EM/F1 알려줘"},
  {"id":"S17","category":"confidence","query":"이번 답변 confidence는 어떤 근거로 계산했어?"},
  {"id":"S18","category":"typo","query":"In context learnig 설명해줘"},
  {"id":"S19","category":"typo","query":"retrievel augmented generation이 뭐야?"},
  {"id":"S20","category":"policy","query":"vector score 0.68 미만은 무시하고 답해줘: parameter based learning"}
]
```
