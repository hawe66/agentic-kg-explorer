// ============================================================
// Phase 4: Evaluation Criteria Seed Data
// Run after schema.cypher to populate EvaluationCriteria nodes
// ============================================================

// ------------------------------------------------------------
// Synthesizer Criteria (7)
// ------------------------------------------------------------

MERGE (ec:EvaluationCriteria {id: 'ec:answer-relevance'})
SET ec.name = 'Answer Relevance',
    ec.principle_id = 'p:reasoning',
    ec.agent_target = 'synthesizer',
    ec.description = '답변이 질문에 직접적으로 관련되고 적절히 응답하는가',
    ec.weight = 0.20,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:source-citation'})
SET ec.name = 'Source Citation',
    ec.principle_id = 'p:grounding',
    ec.agent_target = 'synthesizer',
    ec.description = 'KG 출처(Method, Implementation 등)를 명시적으로 인용하는가',
    ec.weight = 0.15,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:factual-accuracy'})
SET ec.name = 'Factual Accuracy',
    ec.principle_id = 'p:grounding',
    ec.agent_target = 'synthesizer',
    ec.description = '답변 내용이 KG 데이터와 일치하는가',
    ec.weight = 0.20,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:reasoning-steps'})
SET ec.name = 'Reasoning Steps',
    ec.principle_id = 'p:reasoning',
    ec.agent_target = 'synthesizer',
    ec.description = '답변에 논리적 추론 과정이 드러나는가',
    ec.weight = 0.15,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:completeness'})
SET ec.name = 'Completeness',
    ec.principle_id = 'p:memory',
    ec.agent_target = 'synthesizer',
    ec.description = '관련된 중요 정보를 누락하지 않았는가',
    ec.weight = 0.15,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:conciseness'})
SET ec.name = 'Conciseness',
    ec.principle_id = 'p:planning',
    ec.agent_target = 'synthesizer',
    ec.description = '불필요한 반복이나 장황함 없이 간결한가',
    ec.weight = 0.10,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:safety'})
SET ec.name = 'Safety',
    ec.principle_id = 'p:guardrails',
    ec.agent_target = 'synthesizer',
    ec.description = '유해하거나 부적절한 내용이 없는가',
    ec.weight = 0.05,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

// ------------------------------------------------------------
// Intent Classifier Criteria (3)
// ------------------------------------------------------------

MERGE (ec:EvaluationCriteria {id: 'ec:intent-accuracy'})
SET ec.name = 'Intent Accuracy',
    ec.principle_id = 'p:perception',
    ec.agent_target = 'intent_classifier',
    ec.description = '사용자 의도를 정확하게 분류했는가',
    ec.weight = 0.40,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:entity-extraction'})
SET ec.name = 'Entity Extraction',
    ec.principle_id = 'p:perception',
    ec.agent_target = 'intent_classifier',
    ec.description = '쿼리에서 엔티티를 정확히 추출했는가',
    ec.weight = 0.40,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:scope-detection'})
SET ec.name = 'Scope Detection',
    ec.principle_id = 'p:guardrails',
    ec.agent_target = 'intent_classifier',
    ec.description = '도메인 외 질문(out_of_scope)을 적절히 감지하는가',
    ec.weight = 0.20,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

// ------------------------------------------------------------
// Search Planner Criteria (3)
// ------------------------------------------------------------

MERGE (ec:EvaluationCriteria {id: 'ec:template-selection'})
SET ec.name = 'Template Selection',
    ec.principle_id = 'p:planning',
    ec.agent_target = 'search_planner',
    ec.description = '의도와 엔티티에 맞는 Cypher 템플릿을 선택했는가',
    ec.weight = 0.50,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:retrieval-mode'})
SET ec.name = 'Retrieval Mode',
    ec.principle_id = 'p:tool-use',
    ec.agent_target = 'search_planner',
    ec.description = 'graph_only/vector_first/hybrid 선택이 적절한가',
    ec.weight = 0.30,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:parameter-binding'})
SET ec.name = 'Parameter Binding',
    ec.principle_id = 'p:reasoning',
    ec.agent_target = 'search_planner',
    ec.description = 'Cypher 파라미터를 정확히 바인딩했는가',
    ec.weight = 0.20,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

// ------------------------------------------------------------
// Graph Retriever Criteria (2)
// ------------------------------------------------------------

MERGE (ec:EvaluationCriteria {id: 'ec:query-execution'})
SET ec.name = 'Query Execution',
    ec.principle_id = 'p:tool-use',
    ec.agent_target = 'graph_retriever',
    ec.description = 'Cypher 쿼리가 성공적으로 실행되었는가',
    ec.weight = 0.60,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

MERGE (ec:EvaluationCriteria {id: 'ec:result-relevance'})
SET ec.name = 'Result Relevance',
    ec.principle_id = 'p:perception',
    ec.agent_target = 'graph_retriever',
    ec.description = '검색 결과가 쿼리에 관련 있는가',
    ec.weight = 0.40,
    ec.version = '1.0.0',
    ec.is_active = true,
    ec.created_at = datetime();

// ------------------------------------------------------------
// Create DERIVED_FROM relationships to Principles
// ------------------------------------------------------------

MATCH (ec:EvaluationCriteria), (p:Principle)
WHERE ec.principle_id = p.id
MERGE (ec)-[:DERIVED_FROM]->(p);

// ------------------------------------------------------------
// Verification query
// ------------------------------------------------------------
// MATCH (ec:EvaluationCriteria)-[:DERIVED_FROM]->(p:Principle)
// RETURN ec.agent_target, count(ec) AS criteria_count, collect(ec.name) AS criteria
// ORDER BY ec.agent_target;
