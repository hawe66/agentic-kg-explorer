// ============================================================
// Agentic AI Knowledge Graph - Validation Queries
// 데이터 무결성 및 공진화 검증용 쿼리 모음
// ============================================================

// ------------------------------------------------------------
// 1. 기본 통계
// ------------------------------------------------------------

// 노드 타입별 수
MATCH (n)
RETURN labels(n)[0] AS node_type, count(*) AS count
ORDER BY count DESC;

// 관계 타입별 수
MATCH ()-[r]->()
RETURN type(r) AS rel_type, count(*) AS count
ORDER BY count DESC;

// ------------------------------------------------------------
// 2. 데이터 무결성 검증
// ------------------------------------------------------------

// 2.1 Paper 없는 Method 찾기
// (seminal_source도 없는 경우)
MATCH (m:Method)
WHERE NOT (m)<-[:PROPOSES]-(:Document:Paper)
  AND m.seminal_source IS NULL
RETURN m.id, m.name, m.year_introduced
ORDER BY m.name;

// 2.2 Principle에 연결 안 된 Method
MATCH (m:Method)
WHERE NOT (m)-[:ADDRESSES]->(:Principle)
RETURN m.id, m.name
ORDER BY m.name;

// 2.3 Method 없는 Implementation
// (어떤 Method도 구현하지 않는 구현체)
MATCH (i:Implementation)
WHERE NOT (i)-[:IMPLEMENTS]->(:Method)
RETURN i.id, i.name
ORDER BY i.name;

// 2.4 Orphan StandardVersion
// (Standard에 연결되지 않은 버전)
MATCH (sv:StandardVersion)
WHERE NOT (sv)<-[:HAS_VERSION]-(:Standard)
RETURN sv.id, sv.version;

// 2.5 Composite Method인데 USES 관계 없는 경우
MATCH (m:Method {granularity: 'composite'})
WHERE NOT (m)-[:USES]->(:Method)
RETURN m.id, m.name;

// ------------------------------------------------------------
// 3. 공진화 검증
// ------------------------------------------------------------

// 3.1 Principle → Method → Implementation 전체 경로
MATCH path = (p:Principle)<-[:ADDRESSES]-(m:Method)<-[:IMPLEMENTS]-(i:Implementation)
RETURN p.name AS principle, 
       m.name AS method, 
       collect(DISTINCT i.name) AS implementations
ORDER BY p.name, m.name;

// 3.2 각 Principle별 Method 수
MATCH (p:Principle)<-[a:ADDRESSES]-(m:Method)
RETURN p.name, 
       count(DISTINCT m) AS method_count,
       collect(DISTINCT m.name) AS methods
ORDER BY method_count DESC;

// 3.3 각 Principle별 Implementation 수 (간접 연결)
MATCH (p:Principle)<-[:ADDRESSES]-(m:Method)<-[:IMPLEMENTS]-(i:Implementation)
RETURN p.name,
       count(DISTINCT i) AS impl_count,
       collect(DISTINCT i.name) AS implementations
ORDER BY impl_count DESC;

// 3.4 Standard 준수 현황
MATCH (i:Implementation)-[r:COMPLIES_WITH]->(sv:StandardVersion)<-[:HAS_VERSION]-(s:Standard)
RETURN s.name AS standard,
       sv.version,
       collect({impl: i.name, role: r.role, level: r.level}) AS compliances
ORDER BY s.name;

// 3.5 연결 안 된 Principle (Method가 없는 경우)
MATCH (p:Principle)
WHERE NOT (p)<-[:ADDRESSES]-(:Method)
RETURN p.id, p.name;

// ------------------------------------------------------------
// 4. Method 분석
// ------------------------------------------------------------

// 4.1 Method Family별 분포
MATCH (m:Method)
RETURN m.method_family, count(*) AS count
ORDER BY count DESC;

// 4.2 Method Type별 분포
MATCH (m:Method)
RETURN m.method_type, count(*) AS count
ORDER BY count DESC;

// 4.3 Maturity별 분포
MATCH (m:Method)
RETURN m.maturity, count(*) AS count
ORDER BY count DESC;

// 4.4 Multi-principle Methods
// (여러 Principle을 동시에 address하는 Method)
MATCH (m:Method)-[a:ADDRESSES]->(p:Principle)
WITH m, collect({principle: p.name, role: a.role, weight: a.weight}) AS principles
WHERE size(principles) > 1
RETURN m.name, principles
ORDER BY size(principles) DESC;

// ------------------------------------------------------------
// 5. Implementation 분석
// ------------------------------------------------------------

// 5.1 Implementation Type별 분포
MATCH (i:Implementation)
RETURN i.impl_type, count(*) AS count
ORDER BY count DESC;

// 5.2 Support Level별 IMPLEMENTS 분포
MATCH (i:Implementation)-[r:IMPLEMENTS]->(m:Method)
RETURN r.support_level, count(*) AS count
ORDER BY count DESC;

// 5.3 가장 많은 Method를 구현하는 Implementation
MATCH (i:Implementation)-[:IMPLEMENTS]->(m:Method)
WITH i, count(m) AS method_count, collect(m.name) AS methods
ORDER BY method_count DESC
LIMIT 10
RETURN i.name, method_count, methods;

// 5.4 Integration 관계 분석
MATCH (a:Implementation)-[:INTEGRATES_WITH]->(b:Implementation)
RETURN a.name AS from_impl, b.name AS to_impl;

// ------------------------------------------------------------
// 6. Document 분석
// ------------------------------------------------------------

// 6.1 Document → Method 연결
MATCH (d:Document)-[:PROPOSES]->(m:Method)
RETURN d.title, d.year, collect(m.name) AS proposed_methods
ORDER BY d.year DESC;

// 6.2 연도별 Method 제안 수
MATCH (m:Method)
WHERE m.year_introduced IS NOT NULL
RETURN m.year_introduced AS year, count(*) AS count
ORDER BY year;

// ------------------------------------------------------------
// 7. 검색 쿼리 (활용 예시)
// ------------------------------------------------------------

// 7.1 특정 Principle 관련 전체 정보
// 예: Reasoning
MATCH (p:Principle {id: 'p:reasoning'})
OPTIONAL MATCH (p)<-[a:ADDRESSES]-(m:Method)
OPTIONAL MATCH (m)<-[impl:IMPLEMENTS]-(i:Implementation)
RETURN p.name, p.description,
       collect(DISTINCT {method: m.name, role: a.role}) AS methods,
       collect(DISTINCT i.name) AS implementations;

// 7.2 특정 Method를 구현하는 Implementation 상세
// 예: ReAct
MATCH (m:Method {id: 'm:react'})<-[r:IMPLEMENTS]-(i:Implementation)
RETURN m.name AS method,
       i.name AS implementation,
       r.support_level,
       r.evidence,
       i.impl_type,
       i.distribution;

// 7.3 특정 Standard 준수 Implementation
// 예: OTel GenAI
MATCH (s:Standard {id: 'std:otel-genai'})-[:HAS_VERSION]->(sv:StandardVersion)
       <-[c:COMPLIES_WITH]-(i:Implementation)
RETURN s.name, sv.version, i.name, c.role, c.level;

// 7.4 Full-text 검색 (Method)
CALL db.index.fulltext.queryNodes("method_fulltext", "reasoning agent")
YIELD node, score
RETURN node.id, node.name, score
ORDER BY score DESC
LIMIT 10;

// ------------------------------------------------------------
// 8. 데이터 품질 점수
// ------------------------------------------------------------

// 8.1 Method 완성도 점수
// (seminal_source, description, year_introduced 등 유무)
MATCH (m:Method)
RETURN m.name,
       CASE WHEN m.seminal_source IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN m.description IS NOT NULL AND m.description <> '' THEN 1 ELSE 0 END +
       CASE WHEN m.year_introduced IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN size(m.aliases) > 0 THEN 1 ELSE 0 END +
       CASE WHEN size(m.tags) > 0 THEN 1 ELSE 0 END AS completeness_score
ORDER BY completeness_score, m.name;

// 8.2 전체 데이터 품질 요약
MATCH (m:Method)
WITH count(*) AS total_methods,
     count(CASE WHEN m.seminal_source IS NOT NULL THEN 1 END) AS with_source,
     count(CASE WHEN m.description IS NOT NULL AND m.description <> '' THEN 1 END) AS with_desc,
     count(CASE WHEN m.year_introduced IS NOT NULL THEN 1 END) AS with_year
RETURN total_methods,
       with_source, round(100.0 * with_source / total_methods) AS source_pct,
       with_desc, round(100.0 * with_desc / total_methods) AS desc_pct,
       with_year, round(100.0 * with_year / total_methods) AS year_pct;
