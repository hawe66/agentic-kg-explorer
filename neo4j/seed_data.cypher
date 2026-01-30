// ============================================================
// Agentic AI Knowledge Graph - Seed Data
// Version: 1.0.0
// ============================================================

// ------------------------------------------------------------
// 1. Principles (11개 - 불변)
// ------------------------------------------------------------

CREATE (p:Principle {
  id: 'p:perception',
  name: 'Perception',
  description: '환경으로부터 정보를 수집하고 해석하는 능력'
});

CREATE (p:Principle {
  id: 'p:memory',
  name: 'Memory',
  description: '정보를 저장, 검색, 갱신하여 일관성과 학습을 지원'
});

CREATE (p:Principle {
  id: 'p:planning',
  name: 'Planning',
  description: '목표를 하위 과제로 분해하고 실행 순서를 생성'
});

CREATE (p:Principle {
  id: 'p:reasoning',
  name: 'Reasoning',
  description: '논리적 추론을 통해 결론이나 판단을 도출'
});

CREATE (p:Principle {
  id: 'p:tool-use',
  name: 'Tool Use & Action',
  description: '외부 도구를 선택하고 호출하여 작업 완수'
});

CREATE (p:Principle {
  id: 'p:reflection',
  name: 'Reflection',
  description: '자신의 출력/추론/행동을 평가하고 개선'
});

CREATE (p:Principle {
  id: 'p:grounding',
  name: 'Grounding',
  description: '외부 지식에 기반하여 사실적 출력 생성'
});

CREATE (p:Principle {
  id: 'p:learning',
  name: 'Learning',
  description: '피드백과 경험으로부터 지속적 능력 향상'
});

CREATE (p:Principle {
  id: 'p:multi-agent',
  name: 'Multi-Agent Collaboration',
  description: '여러 Agent 간 협력/조정 메커니즘'
});

CREATE (p:Principle {
  id: 'p:guardrails',
  name: 'Guardrails',
  description: '안전성, 보안, 규정 준수를 위한 제어'
});

CREATE (p:Principle {
  id: 'p:tracing',
  name: 'Tracing',
  description: '실행 흐름과 성능을 관찰하고 분석'
});

// ------------------------------------------------------------
// 2. Standards
// ------------------------------------------------------------

CREATE (s:Standard {
  id: 'std:mcp',
  name: 'Model Context Protocol',
  aliases: ['MCP'],
  standard_type: 'protocol',
  steward: 'Anthropic',
  governance: 'company',
  status: 'stable',
  versioning_scheme: 'date',
  first_published: date('2024-11-25'),
  tags: ['tool-integration', 'context', 'ai-apps']
});

CREATE (s:Standard {
  id: 'std:a2a',
  name: 'Agent2Agent Protocol',
  aliases: ['A2A'],
  standard_type: 'protocol',
  steward: 'Google',
  governance: 'company',
  status: 'draft',
  versioning_scheme: 'semver',
  first_published: date('2025-04-01'),
  tags: ['multi-agent', 'interoperability']
});

CREATE (s:Standard {
  id: 'std:otel-genai',
  name: 'OpenTelemetry GenAI Semantic Conventions',
  aliases: ['OTel GenAI semconv'],
  standard_type: 'semantic_convention',
  steward: 'CNCF',
  governance: 'foundation',
  status: 'experimental',
  versioning_scheme: 'semver',
  first_published: date('2024-06-01'),
  tags: ['observability', 'tracing', 'genai']
});

// ------------------------------------------------------------
// 3. Standard Versions
// ------------------------------------------------------------

CREATE (sv:StandardVersion {
  id: 'stdv:mcp@2025-03-26',
  version: '2025-03-26',
  status: 'stable',
  published_at: date('2025-03-26'),
  tags: ['latest']
});

CREATE (sv:StandardVersion {
  id: 'stdv:a2a@1.0-draft',
  version: '1.0-draft',
  status: 'draft',
  published_at: date('2025-04-01'),
  tags: ['initial']
});

CREATE (sv:StandardVersion {
  id: 'stdv:otel-genai@1.30',
  version: '1.30.0',
  status: 'experimental',
  published_at: date('2025-01-01'),
  tags: ['development']
});

// Link versions to standards
MATCH (s:Standard {id: 'std:mcp'}), (sv:StandardVersion {id: 'stdv:mcp@2025-03-26'})
CREATE (s)-[:HAS_VERSION]->(sv);

MATCH (s:Standard {id: 'std:a2a'}), (sv:StandardVersion {id: 'stdv:a2a@1.0-draft'})
CREATE (s)-[:HAS_VERSION]->(sv);

MATCH (s:Standard {id: 'std:otel-genai'}), (sv:StandardVersion {id: 'stdv:otel-genai@1.30'})
CREATE (s)-[:HAS_VERSION]->(sv);

// ------------------------------------------------------------
// 4. Methods - Prompting/Decoding
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:cot',
  name: 'Chain-of-Thought',
  aliases: ['CoT'],
  method_family: 'prompting_decoding',
  method_type: 'prompt_pattern',
  granularity: 'atomic',
  method_kind: ['reasoning-elicitation'],
  description: 'LLM이 최종 답변 전에 중간 추론 단계를 생성하도록 유도하는 프롬프팅 기법',
  year_introduced: 2022,
  maturity: 'production',
  tags: ['reasoning', 'prompting']
});

CREATE (m:Method {
  id: 'm:self-consistency',
  name: 'Self-Consistency',
  aliases: ['SC'],
  method_family: 'prompting_decoding',
  method_type: 'decoding_strategy',
  granularity: 'atomic',
  method_kind: ['ensemble', 'voting'],
  description: '여러 추론 경로를 샘플링하고 다수결로 최종 답변을 선택하는 디코딩 전략',
  year_introduced: 2022,
  maturity: 'production',
  tags: ['reasoning', 'decoding']
});

CREATE (m:Method {
  id: 'm:cot-sc',
  name: 'CoT + Self-Consistency',
  aliases: ['CoT-SC'],
  method_family: 'prompting_decoding',
  method_type: 'prompt_pattern',
  granularity: 'composite',
  method_kind: ['reasoning-elicitation', 'ensemble'],
  description: 'Chain-of-Thought와 Self-Consistency를 결합한 추론 기법',
  year_introduced: 2022,
  maturity: 'production',
  tags: ['reasoning', 'composite']
});

CREATE (m:Method {
  id: 'm:tot',
  name: 'Tree-of-Thoughts',
  aliases: ['ToT'],
  method_family: 'prompting_decoding',
  method_type: 'search_planning_algo',
  granularity: 'atomic',
  method_kind: ['tree-search', 'deliberate-reasoning'],
  description: '트리 구조로 여러 추론 경로를 탐색하고 평가하는 기법',
  year_introduced: 2023,
  maturity: 'research',
  tags: ['reasoning', 'planning', 'search']
});

CREATE (m:Method {
  id: 'm:got',
  name: 'Graph-of-Thoughts',
  aliases: ['GoT'],
  method_family: 'prompting_decoding',
  method_type: 'search_planning_algo',
  granularity: 'atomic',
  method_kind: ['graph-search', 'non-linear-reasoning'],
  description: '그래프 구조로 추론 단위를 연결하고 병합하는 기법',
  year_introduced: 2023,
  maturity: 'research',
  tags: ['reasoning', 'planning', 'graph']
});

// ------------------------------------------------------------
// 5. Methods - Agent Loop Patterns
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:react',
  name: 'ReAct',
  aliases: ['Reason+Act'],
  method_family: 'agent_loop_pattern',
  method_type: 'agent_control_loop',
  granularity: 'atomic',
  method_kind: ['interleaved-reasoning-acting'],
  description: 'Reasoning과 Acting을 교대로 수행하는 에이전트 루프 패턴',
  year_introduced: 2022,
  maturity: 'production',
  tags: ['agent', 'tool-use', 'reasoning']
});

CREATE (m:Method {
  id: 'm:rewoo',
  name: 'ReWOO',
  aliases: ['Reasoning Without Observation'],
  method_family: 'agent_loop_pattern',
  method_type: 'agent_control_loop',
  granularity: 'atomic',
  method_kind: ['plan-then-execute'],
  description: '계획을 먼저 세우고 관찰 없이 실행한 후 결과를 통합하는 패턴',
  year_introduced: 2023,
  maturity: 'research',
  tags: ['agent', 'planning', 'efficiency']
});

CREATE (m:Method {
  id: 'm:lats',
  name: 'LATS',
  aliases: ['Language Agent Tree Search'],
  method_family: 'agent_loop_pattern',
  method_type: 'search_planning_algo',
  granularity: 'atomic',
  method_kind: ['MCTS', 'tree-search', 'self-reflection'],
  description: 'MCTS 기반의 에이전트 트리 탐색과 자기 성찰을 결합한 기법',
  year_introduced: 2024,
  maturity: 'research',
  tags: ['agent', 'planning', 'reflection', 'search']
});

// ------------------------------------------------------------
// 6. Methods - Workflow Orchestration
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:workflow-graph',
  name: 'Workflow Graph Orchestration',
  aliases: ['State Graph', 'DAG Workflow'],
  method_family: 'workflow_orchestration',
  method_type: 'workflow_pattern',
  granularity: 'atomic',
  method_kind: ['state-machine', 'deterministic-flow'],
  description: '사전 정의된 상태 그래프로 워크플로우를 제어하는 패턴',
  year_introduced: 2024,
  maturity: 'production',
  tags: ['orchestration', 'workflow', 'deterministic']
});

// ------------------------------------------------------------
// 7. Methods - Retrieval/Grounding
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:rag',
  name: 'Retrieval-Augmented Generation',
  aliases: ['RAG'],
  method_family: 'retrieval_grounding',
  method_type: 'retrieval_indexing',
  granularity: 'atomic',
  method_kind: ['retrieve-then-generate'],
  description: '외부 지식을 검색하여 생성에 활용하는 기법',
  year_introduced: 2020,
  maturity: 'production',
  tags: ['grounding', 'retrieval', 'generation']
});

CREATE (m:Method {
  id: 'm:graphrag',
  name: 'GraphRAG',
  aliases: ['Graph-based RAG'],
  method_family: 'retrieval_grounding',
  method_type: 'retrieval_indexing',
  granularity: 'atomic',
  method_kind: ['knowledge-graph', 'hierarchical-summarization'],
  description: '지식 그래프와 계층적 요약을 활용한 RAG 기법',
  year_introduced: 2024,
  maturity: 'production',
  tags: ['grounding', 'knowledge-graph', 'summarization']
});

CREATE (m:Method {
  id: 'm:hipporag',
  name: 'HippoRAG',
  aliases: [],
  method_family: 'retrieval_grounding',
  method_type: 'retrieval_indexing',
  granularity: 'atomic',
  method_kind: ['hippocampus-inspired', 'associative-memory'],
  description: '해마 영감 연상 기억을 활용한 RAG 기법',
  year_introduced: 2024,
  maturity: 'research',
  tags: ['grounding', 'memory', 'neuroscience-inspired']
});

CREATE (m:Method {
  id: 'm:raptor',
  name: 'RAPTOR',
  aliases: [],
  method_family: 'retrieval_grounding',
  method_type: 'retrieval_indexing',
  granularity: 'atomic',
  method_kind: ['recursive-summarization', 'tree-indexing'],
  description: '재귀적 요약과 트리 인덱싱을 활용한 RAG 기법',
  year_introduced: 2024,
  maturity: 'research',
  tags: ['grounding', 'summarization', 'hierarchical']
});

CREATE (m:Method {
  id: 'm:lightrag',
  name: 'LightRAG',
  aliases: [],
  method_family: 'retrieval_grounding',
  method_type: 'retrieval_indexing',
  granularity: 'atomic',
  method_kind: ['lightweight', 'efficient'],
  description: '경량화된 효율적인 RAG 기법',
  year_introduced: 2024,
  maturity: 'research',
  tags: ['grounding', 'efficiency']
});

// ------------------------------------------------------------
// 8. Methods - Memory System
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:memgpt',
  name: 'MemGPT',
  aliases: [],
  method_family: 'memory_system',
  method_type: 'memory_architecture',
  granularity: 'atomic',
  method_kind: ['hierarchical-memory', 'virtual-context'],
  description: '계층적 메모리와 가상 컨텍스트 관리를 활용한 메모리 아키텍처',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['memory', 'context-management', 'long-term']
});

CREATE (m:Method {
  id: 'm:temporal-kg-memory',
  name: 'Temporal KG Memory',
  aliases: ['Graphiti'],
  method_family: 'memory_system',
  method_type: 'memory_architecture',
  granularity: 'atomic',
  method_kind: ['temporal-knowledge-graph', 'episodic'],
  description: '시간적 지식 그래프 기반 메모리 아키텍처',
  year_introduced: 2025,
  maturity: 'research',
  tags: ['memory', 'knowledge-graph', 'temporal']
});

// ------------------------------------------------------------
// 9. Methods - Reflection/Verification
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:reflexion',
  name: 'Reflexion',
  aliases: [],
  method_family: 'reflection_verification',
  method_type: 'agent_control_loop',
  granularity: 'atomic',
  method_kind: ['self-reflection', 'episodic-memory'],
  description: '실패 경험을 에피소딕 메모리에 저장하고 성찰하는 에이전트 기법',
  year_introduced: 2023,
  maturity: 'research',
  tags: ['reflection', 'memory', 'learning']
});

CREATE (m:Method {
  id: 'm:self-refine',
  name: 'Self-Refine',
  aliases: [],
  method_family: 'reflection_verification',
  method_type: 'prompt_pattern',
  granularity: 'atomic',
  method_kind: ['iterative-refinement', 'self-feedback'],
  description: '자체 피드백을 통해 출력을 반복적으로 개선하는 기법',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['reflection', 'refinement']
});

CREATE (m:Method {
  id: 'm:critic',
  name: 'CRITIC',
  aliases: [],
  method_family: 'reflection_verification',
  method_type: 'agent_control_loop',
  granularity: 'atomic',
  method_kind: ['tool-based-verification', 'external-feedback'],
  description: '외부 도구를 활용하여 출력을 검증하고 수정하는 기법',
  year_introduced: 2024,
  maturity: 'research',
  tags: ['reflection', 'tool-use', 'verification']
});

CREATE (m:Method {
  id: 'm:cove',
  name: 'Chain-of-Verification',
  aliases: ['CoVe'],
  method_family: 'reflection_verification',
  method_type: 'prompt_pattern',
  granularity: 'atomic',
  method_kind: ['verification-chain', 'factual-checking'],
  description: '검증 질문을 생성하고 답변하여 사실성을 확인하는 기법',
  year_introduced: 2023,
  maturity: 'research',
  tags: ['reflection', 'verification', 'factuality']
});

// ------------------------------------------------------------
// 10. Methods - Multi-Agent Coordination
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:camel',
  name: 'CAMEL',
  aliases: ['Communicative Agents'],
  method_family: 'multi_agent_coordination',
  method_type: 'coordination_pattern',
  granularity: 'atomic',
  method_kind: ['role-playing', 'cooperative-debate'],
  description: '역할 기반 협력 대화를 통한 멀티에이전트 조정 패턴',
  year_introduced: 2023,
  maturity: 'research',
  tags: ['multi-agent', 'role-playing', 'cooperation']
});

CREATE (m:Method {
  id: 'm:metagpt',
  name: 'MetaGPT',
  aliases: [],
  method_family: 'multi_agent_coordination',
  method_type: 'coordination_pattern',
  granularity: 'atomic',
  method_kind: ['sop-driven', 'role-specialization'],
  description: 'SOP 기반 역할 전문화 멀티에이전트 프레임워크 패턴',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['multi-agent', 'sop', 'software-development']
});

// ------------------------------------------------------------
// 11. Methods - Training/Alignment
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:rlhf',
  name: 'RLHF',
  aliases: ['Reinforcement Learning from Human Feedback'],
  method_family: 'training_alignment',
  method_type: 'training_objective',
  granularity: 'atomic',
  method_kind: ['preference-learning', 'reward-model'],
  description: '인간 피드백을 통한 강화학습 정렬 기법',
  year_introduced: 2022,
  maturity: 'standardized',
  tags: ['alignment', 'training', 'human-feedback']
});

CREATE (m:Method {
  id: 'm:dpo',
  name: 'DPO',
  aliases: ['Direct Preference Optimization'],
  method_family: 'training_alignment',
  method_type: 'training_objective',
  granularity: 'atomic',
  method_kind: ['direct-optimization', 'preference-learning'],
  description: '리워드 모델 없이 직접 선호도를 최적화하는 정렬 기법',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['alignment', 'training', 'efficiency']
});

CREATE (m:Method {
  id: 'm:icl',
  name: 'In-Context Learning',
  aliases: ['ICL', 'Few-shot Learning'],
  method_family: 'prompting_decoding',
  method_type: 'prompt_pattern',
  granularity: 'atomic',
  method_kind: ['demonstration-based', 'non-parametric'],
  description: '컨텍스트 내 예시를 통해 태스크를 학습하는 기법',
  year_introduced: 2020,
  maturity: 'standardized',
  tags: ['learning', 'prompting', 'few-shot']
});

// ------------------------------------------------------------
// 12. Methods - Guardrails (NEW)
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:input-validation',
  name: 'Input Validation',
  aliases: ['Prompt Injection Defense'],
  method_family: 'safety_control',
  method_type: 'safety_classifier_or_policy',
  granularity: 'atomic',
  method_kind: ['input-filtering', 'injection-prevention'],
  description: '악의적 입력 및 프롬프트 인젝션을 탐지하고 차단하는 기법',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['safety', 'security', 'validation']
});

CREATE (m:Method {
  id: 'm:output-validation',
  name: 'Output Validation',
  aliases: ['Structured Output Enforcement'],
  method_family: 'safety_control',
  method_type: 'safety_classifier_or_policy',
  granularity: 'atomic',
  method_kind: ['output-validation', 'schema-enforcement'],
  description: 'LLM 출력이 정의된 스키마와 제약사항을 준수하도록 검증하는 기법',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['safety', 'validation', 'structured-output']
});

CREATE (m:Method {
  id: 'm:content-moderation',
  name: 'Content Moderation',
  aliases: ['Safety Filtering'],
  method_family: 'safety_control',
  method_type: 'safety_classifier_or_policy',
  granularity: 'atomic',
  method_kind: ['toxicity-detection', 'policy-enforcement'],
  description: '유해 콘텐츠, 편향, 개인정보 등을 탐지하고 필터링하는 기법',
  year_introduced: 2023,
  maturity: 'production',
  tags: ['safety', 'moderation', 'compliance']
});

// ------------------------------------------------------------
// 13. Methods - Tracing/Observability (NEW)
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:span-tracing',
  name: 'Span-based Tracing',
  aliases: ['Distributed Tracing'],
  method_family: 'observability_tracing',
  method_type: 'instrumentation_pattern',
  granularity: 'atomic',
  method_kind: ['span-context', 'hierarchical-tracing'],
  description: 'OpenTelemetry 스타일의 Span 기반 실행 추적 기법',
  year_introduced: 2024,
  maturity: 'production',
  tags: ['observability', 'tracing', 'opentelemetry']
});

CREATE (m:Method {
  id: 'm:llm-observability',
  name: 'LLM Observability',
  aliases: ['GenAI Monitoring'],
  method_family: 'observability_tracing',
  method_type: 'instrumentation_pattern',
  granularity: 'atomic',
  method_kind: ['token-tracking', 'cost-monitoring', 'latency-profiling'],
  description: 'LLM 호출의 토큰, 비용, 지연시간 등을 추적하는 관찰 기법',
  year_introduced: 2024,
  maturity: 'production',
  tags: ['observability', 'monitoring', 'llm']
});

// ------------------------------------------------------------
// 14. Methods - Perception (NEW)
// ------------------------------------------------------------

CREATE (m:Method {
  id: 'm:multimodal-fusion',
  name: 'Multimodal Fusion',
  aliases: ['Cross-modal Integration'],
  method_family: 'prompting_decoding',
  method_type: 'prompt_pattern',
  granularity: 'atomic',
  method_kind: ['vision-language', 'multimodal-reasoning'],
  description: '텍스트, 이미지, 오디오 등 다중 모달리티를 통합하여 처리하는 기법',
  year_introduced: 2024,
  maturity: 'production',
  tags: ['perception', 'multimodal', 'vision']
});

// ------------------------------------------------------------
// 12. Method USES Relationships (Composite)
// ------------------------------------------------------------

MATCH (cot_sc:Method {id: 'm:cot-sc'}), (cot:Method {id: 'm:cot'})
CREATE (cot_sc)-[:USES]->(cot);

MATCH (cot_sc:Method {id: 'm:cot-sc'}), (sc:Method {id: 'm:self-consistency'})
CREATE (cot_sc)-[:USES]->(sc);

// ------------------------------------------------------------
// 13. Method ADDRESSES Principle Relationships
// ------------------------------------------------------------

// Reasoning methods
MATCH (m:Method {id: 'm:cot'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:self-consistency'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:cot-sc'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:tot'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 0.8}]->(p);

MATCH (m:Method {id: 'm:tot'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.6}]->(p);

MATCH (m:Method {id: 'm:got'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 0.8}]->(p);

MATCH (m:Method {id: 'm:got'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.6}]->(p);

// Agent loop methods
MATCH (m:Method {id: 'm:react'}), (p:Principle {id: 'p:tool-use'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:react'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.7}]->(p);

MATCH (m:Method {id: 'm:rewoo'}), (p:Principle {id: 'p:tool-use'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:rewoo'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.8}]->(p);

MATCH (m:Method {id: 'm:lats'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 0.9}]->(p);

MATCH (m:Method {id: 'm:lats'}), (p:Principle {id: 'p:reflection'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.7}]->(p);

// Workflow methods
MATCH (m:Method {id: 'm:workflow-graph'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// Grounding methods
MATCH (m:Method {id: 'm:rag'}), (p:Principle {id: 'p:grounding'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:rag'}), (p:Principle {id: 'p:tool-use'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.5}]->(p);

MATCH (m:Method {id: 'm:graphrag'}), (p:Principle {id: 'p:grounding'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:hipporag'}), (p:Principle {id: 'p:grounding'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 0.9}]->(p);

MATCH (m:Method {id: 'm:hipporag'}), (p:Principle {id: 'p:memory'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.7}]->(p);

MATCH (m:Method {id: 'm:raptor'}), (p:Principle {id: 'p:grounding'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:lightrag'}), (p:Principle {id: 'p:grounding'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// Memory methods
MATCH (m:Method {id: 'm:memgpt'}), (p:Principle {id: 'p:memory'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:memgpt'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.5}]->(p);

MATCH (m:Method {id: 'm:temporal-kg-memory'}), (p:Principle {id: 'p:memory'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// Reflection methods
MATCH (m:Method {id: 'm:reflexion'}), (p:Principle {id: 'p:reflection'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:reflexion'}), (p:Principle {id: 'p:memory'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.7}]->(p);

MATCH (m:Method {id: 'm:self-refine'}), (p:Principle {id: 'p:reflection'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:critic'}), (p:Principle {id: 'p:reflection'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 0.9}]->(p);

MATCH (m:Method {id: 'm:critic'}), (p:Principle {id: 'p:tool-use'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.7}]->(p);

MATCH (m:Method {id: 'm:cove'}), (p:Principle {id: 'p:reflection'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:cove'}), (p:Principle {id: 'p:reasoning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.6}]->(p);

// Multi-agent methods
MATCH (m:Method {id: 'm:camel'}), (p:Principle {id: 'p:multi-agent'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:metagpt'}), (p:Principle {id: 'p:multi-agent'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:metagpt'}), (p:Principle {id: 'p:planning'})
CREATE (m)-[:ADDRESSES {role: 'secondary', weight: 0.6}]->(p);

// Training/Alignment methods
MATCH (m:Method {id: 'm:rlhf'}), (p:Principle {id: 'p:learning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:dpo'}), (p:Principle {id: 'p:learning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:icl'}), (p:Principle {id: 'p:learning'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// Guardrails methods (NEW)
MATCH (m:Method {id: 'm:input-validation'}), (p:Principle {id: 'p:guardrails'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:output-validation'}), (p:Principle {id: 'p:guardrails'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:content-moderation'}), (p:Principle {id: 'p:guardrails'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// Tracing methods (NEW)
MATCH (m:Method {id: 'm:span-tracing'}), (p:Principle {id: 'p:tracing'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

MATCH (m:Method {id: 'm:llm-observability'}), (p:Principle {id: 'p:tracing'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// Perception methods (NEW)
MATCH (m:Method {id: 'm:multimodal-fusion'}), (p:Principle {id: 'p:perception'})
CREATE (m)-[:ADDRESSES {role: 'primary', weight: 1.0}]->(p);

// ------------------------------------------------------------
// 14. Implementations
// ------------------------------------------------------------

// Frameworks
CREATE (i:Implementation {
  id: 'impl:langchain',
  name: 'LangChain',
  aliases: [],
  impl_type: 'framework',
  distribution: 'oss',
  maintainer: 'LangChain Inc.',
  license: 'MIT',
  source_repo: 'https://github.com/langchain-ai/langchain',
  languages: ['Python', 'JavaScript'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['agent', 'rag', 'orchestration']
});

CREATE (i:Implementation {
  id: 'impl:langgraph',
  name: 'LangGraph',
  aliases: [],
  impl_type: 'framework',
  distribution: 'oss',
  maintainer: 'LangChain Inc.',
  license: 'MIT',
  source_repo: 'https://github.com/langchain-ai/langgraph',
  languages: ['Python', 'JavaScript'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['workflow', 'agent', 'state-machine']
});

CREATE (i:Implementation {
  id: 'impl:llamaindex',
  name: 'LlamaIndex',
  aliases: ['GPT Index'],
  impl_type: 'framework',
  distribution: 'oss',
  maintainer: 'LlamaIndex Inc.',
  license: 'MIT',
  source_repo: 'https://github.com/run-llama/llama_index',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['rag', 'indexing', 'retrieval']
});

CREATE (i:Implementation {
  id: 'impl:autogen',
  name: 'AutoGen',
  aliases: [],
  impl_type: 'framework',
  distribution: 'oss',
  maintainer: 'Microsoft',
  license: 'MIT',
  source_repo: 'https://github.com/microsoft/autogen',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['multi-agent', 'conversation', 'orchestration']
});

CREATE (i:Implementation {
  id: 'impl:crewai',
  name: 'CrewAI',
  aliases: [],
  impl_type: 'framework',
  distribution: 'oss',
  maintainer: 'CrewAI Inc.',
  license: 'MIT',
  source_repo: 'https://github.com/crewAIInc/crewAI',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['multi-agent', 'role-based', 'orchestration']
});

CREATE (i:Implementation {
  id: 'impl:openai-agents-sdk',
  name: 'OpenAI Agents SDK',
  aliases: ['Swarm'],
  impl_type: 'sdk',
  distribution: 'oss',
  maintainer: 'OpenAI',
  license: 'MIT',
  source_repo: 'https://github.com/openai/openai-agents-python',
  languages: ['Python'],
  platforms: ['cloud'],
  status: 'active',
  tags: ['agent', 'tool-use', 'handoff']
});

CREATE (i:Implementation {
  id: 'impl:semantic-kernel',
  name: 'Semantic Kernel',
  aliases: ['SK'],
  impl_type: 'sdk',
  distribution: 'oss',
  maintainer: 'Microsoft',
  license: 'MIT',
  source_repo: 'https://github.com/microsoft/semantic-kernel',
  languages: ['Python', 'C#', 'Java'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['orchestration', 'plugin', 'enterprise']
});

// Memory
CREATE (i:Implementation {
  id: 'impl:mem0',
  name: 'Mem0',
  aliases: ['EmbedChain Memory'],
  impl_type: 'library',
  distribution: 'oss',
  maintainer: 'Mem0.ai',
  license: 'Apache-2.0',
  source_repo: 'https://github.com/mem0ai/mem0',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['memory', 'personalization', 'long-term']
});

CREATE (i:Implementation {
  id: 'impl:zep',
  name: 'Zep',
  aliases: [],
  impl_type: 'service',
  distribution: 'managed',
  maintainer: 'Zep AI',
  license: 'Apache-2.0',
  source_repo: 'https://github.com/getzep/zep',
  languages: ['Python', 'Go'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['memory', 'knowledge-graph', 'temporal']
});

// Grounding
CREATE (i:Implementation {
  id: 'impl:ms-graphrag',
  name: 'microsoft/graphrag',
  aliases: ['GraphRAG'],
  impl_type: 'library',
  distribution: 'oss',
  maintainer: 'Microsoft',
  license: 'MIT',
  source_repo: 'https://github.com/microsoft/graphrag',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['rag', 'knowledge-graph', 'summarization']
});

// Observability
CREATE (i:Implementation {
  id: 'impl:langsmith',
  name: 'LangSmith',
  aliases: [],
  impl_type: 'service',
  distribution: 'managed',
  maintainer: 'LangChain Inc.',
  license: 'Proprietary',
  source_repo: null,
  languages: ['Python', 'JavaScript'],
  platforms: ['cloud'],
  status: 'active',
  tags: ['observability', 'tracing', 'evaluation']
});

CREATE (i:Implementation {
  id: 'impl:langfuse',
  name: 'Langfuse',
  aliases: [],
  impl_type: 'service',
  distribution: 'oss',
  maintainer: 'Langfuse GmbH',
  license: 'MIT',
  source_repo: 'https://github.com/langfuse/langfuse',
  languages: ['TypeScript', 'Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['observability', 'tracing', 'analytics']
});

// Guardrails
CREATE (i:Implementation {
  id: 'impl:nemo-guardrails',
  name: 'NeMo Guardrails',
  aliases: [],
  impl_type: 'library',
  distribution: 'oss',
  maintainer: 'NVIDIA',
  license: 'Apache-2.0',
  source_repo: 'https://github.com/NVIDIA/NeMo-Guardrails',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['guardrails', 'safety', 'dialogue']
});

CREATE (i:Implementation {
  id: 'impl:guardrails-ai',
  name: 'Guardrails AI',
  aliases: [],
  impl_type: 'library',
  distribution: 'oss',
  maintainer: 'Guardrails AI Inc.',
  license: 'Apache-2.0',
  source_repo: 'https://github.com/guardrails-ai/guardrails',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['guardrails', 'validation', 'structured-output']
});

CREATE (i:Implementation {
  id: 'impl:llm-guard',
  name: 'LLM Guard',
  aliases: [],
  impl_type: 'library',
  distribution: 'oss',
  maintainer: 'Protect AI',
  license: 'MIT',
  source_repo: 'https://github.com/protectai/llm-guard',
  languages: ['Python'],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['guardrails', 'security', 'moderation']
});

CREATE (i:Implementation {
  id: 'impl:llamaguard',
  name: 'LlamaGuard',
  aliases: ['Llama Guard'],
  impl_type: 'model',
  distribution: 'oss',
  maintainer: 'Meta',
  license: 'Llama Community License',
  source_repo: 'https://github.com/meta-llama/PurpleLlama',
  languages: [],
  platforms: ['cloud', 'on-prem'],
  status: 'active',
  tags: ['guardrails', 'safety', 'classifier']
});

// ------------------------------------------------------------
// 15. Implementation IMPLEMENTS Method Relationships
// ------------------------------------------------------------

MATCH (i:Implementation {id: 'impl:langchain'}), (m:Method {id: 'm:react'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:langchain'}), (m:Method {id: 'm:rag'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:langgraph'}), (m:Method {id: 'm:workflow-graph'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:langgraph'}), (m:Method {id: 'm:react'})
CREATE (i)-[:IMPLEMENTS {support_level: 'template', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:llamaindex'}), (m:Method {id: 'm:rag'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:autogen'}), (m:Method {id: 'm:camel'})
CREATE (i)-[:IMPLEMENTS {support_level: 'first_class', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:crewai'}), (m:Method {id: 'm:metagpt'})
CREATE (i)-[:IMPLEMENTS {support_level: 'integration', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:mem0'}), (m:Method {id: 'm:memgpt'})
CREATE (i)-[:IMPLEMENTS {support_level: 'integration', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:zep'}), (m:Method {id: 'm:temporal-kg-memory'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:ms-graphrag'}), (m:Method {id: 'm:graphrag'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'both'}]->(m);

// NEW: Add IMPLEMENTS relationships for orphan implementations
MATCH (i:Implementation {id: 'impl:openai-agents-sdk'}), (m:Method {id: 'm:react'})
CREATE (i)-[:IMPLEMENTS {support_level: 'first_class', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:semantic-kernel'}), (m:Method {id: 'm:workflow-graph'})
CREATE (i)-[:IMPLEMENTS {support_level: 'first_class', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:nemo-guardrails'}), (m:Method {id: 'm:input-validation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:nemo-guardrails'}), (m:Method {id: 'm:content-moderation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'first_class', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:guardrails-ai'}), (m:Method {id: 'm:output-validation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:guardrails-ai'}), (m:Method {id: 'm:input-validation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'first_class', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:llm-guard'}), (m:Method {id: 'm:content-moderation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:llm-guard'}), (m:Method {id: 'm:input-validation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'first_class', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:llamaguard'}), (m:Method {id: 'm:content-moderation'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'both'}]->(m);

MATCH (i:Implementation {id: 'impl:langsmith'}), (m:Method {id: 'm:span-tracing'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:langsmith'}), (m:Method {id: 'm:llm-observability'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:langfuse'}), (m:Method {id: 'm:span-tracing'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

MATCH (i:Implementation {id: 'impl:langfuse'}), (m:Method {id: 'm:llm-observability'})
CREATE (i)-[:IMPLEMENTS {support_level: 'core', evidence: 'doc'}]->(m);

// ------------------------------------------------------------
// 16. Implementation COMPLIES_WITH Standard Relationships
// ------------------------------------------------------------

MATCH (i:Implementation {id: 'impl:langsmith'}), (sv:StandardVersion {id: 'stdv:otel-genai@1.30'})
CREATE (i)-[:COMPLIES_WITH {role: 'exporter', level: 'claims'}]->(sv);

MATCH (i:Implementation {id: 'impl:langfuse'}), (sv:StandardVersion {id: 'stdv:otel-genai@1.30'})
CREATE (i)-[:COMPLIES_WITH {role: 'collector', level: 'claims'}]->(sv);

// ------------------------------------------------------------
// 17. Implementation INTEGRATES_WITH Relationships
// ------------------------------------------------------------

MATCH (a:Implementation {id: 'impl:langgraph'}), (b:Implementation {id: 'impl:langchain'})
CREATE (a)-[:INTEGRATES_WITH]->(b);

MATCH (a:Implementation {id: 'impl:langsmith'}), (b:Implementation {id: 'impl:langchain'})
CREATE (a)-[:INTEGRATES_WITH]->(b);

MATCH (a:Implementation {id: 'impl:langsmith'}), (b:Implementation {id: 'impl:langgraph'})
CREATE (a)-[:INTEGRATES_WITH]->(b);

// ------------------------------------------------------------
// 18. Sample Documents (Papers)
// ------------------------------------------------------------

CREATE (d:Document:Paper {
  id: 'doc:react-2022',
  title: 'ReAct: Synergizing Reasoning and Acting in Language Models',
  authors: ['Shunyu Yao', 'Jeffrey Zhao', 'Dian Yu', 'Nan Du', 'Izhak Shafran', 'Karthik Narasimhan', 'Yuan Cao'],
  venue: 'ICLR',
  year: 2023,
  url: 'https://arxiv.org/abs/2210.03629',
  abstract: 'We propose ReAct, a general paradigm to synergize reasoning and acting in language models.',
  tags: ['agent', 'reasoning', 'tool-use']
});

CREATE (d:Document:Paper {
  id: 'doc:cot-2022',
  title: 'Chain-of-Thought Prompting Elicits Reasoning in Large Language Models',
  authors: ['Jason Wei', 'Xuezhi Wang', 'Dale Schuurmans', 'Maarten Bosma', 'Ed Chi', 'Quoc Le', 'Denny Zhou'],
  venue: 'NeurIPS',
  year: 2022,
  url: 'https://arxiv.org/abs/2201.11903',
  abstract: 'We explore how generating a chain of thought can improve the reasoning abilities of large language models.',
  tags: ['reasoning', 'prompting']
});

CREATE (d:Document:Paper {
  id: 'doc:rag-2020',
  title: 'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks',
  authors: ['Patrick Lewis', 'Ethan Perez', 'Aleksandra Piktus', 'Fabio Petroni', 'Vladimir Karpukhin', 'Naman Goyal', 'Heinrich Küttler', 'Mike Lewis', 'Wen-tau Yih', 'Tim Rocktäschel', 'Sebastian Riedel', 'Douwe Kiela'],
  venue: 'NeurIPS',
  year: 2020,
  url: 'https://arxiv.org/abs/2005.11401',
  abstract: 'We introduce RAG models which combine pre-trained parametric and non-parametric memory for language generation.',
  tags: ['rag', 'retrieval', 'generation']
});

// Document PROPOSES Method
MATCH (d:Document {id: 'doc:react-2022'}), (m:Method {id: 'm:react'})
CREATE (d)-[:PROPOSES]->(m);

MATCH (d:Document {id: 'doc:cot-2022'}), (m:Method {id: 'm:cot'})
CREATE (d)-[:PROPOSES]->(m);

MATCH (d:Document {id: 'doc:rag-2020'}), (m:Method {id: 'm:rag'})
CREATE (d)-[:PROPOSES]->(m);

// Link seminal_source
MATCH (m:Method {id: 'm:react'})
SET m.seminal_source = 'doc:react-2022';

MATCH (m:Method {id: 'm:cot'})
SET m.seminal_source = 'doc:cot-2022';

MATCH (m:Method {id: 'm:rag'})
SET m.seminal_source = 'doc:rag-2020';
