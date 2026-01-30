# Changelog

All notable changes to the Agentic AI Knowledge Graph Explorer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-29

### Phase 1: Foundation Complete ✅

#### Added

**Core Infrastructure**
- Neo4j client implementation with connection pooling (`src/graph/client.py` - 520 lines)
- Comprehensive Pydantic models for all node and relationship types (`src/graph/schema.py` - 437 lines)
- Configuration management using dotenv (`config/settings.py`)

**Database Schema**
- 11 immutable Principles as foundation layer
- Method classification system with `method_family`, `method_type`, `granularity`
- Standard version separation (`Standard` + `StandardVersion`)
- Relationship types: ADDRESSES, IMPLEMENTS, COMPLIES_WITH, USES, PROPOSES, HAS_VERSION, INTEGRATES_WITH
- Constraints and indexes for data integrity (`neo4j/schema.cypher` - 37 statements)

**Seed Data**
- 11 Principles with complete coverage
- 31 Methods across all method families
- 16 Implementations (LangChain, CrewAI, AutoGen, etc.)
- 3 Standards (MCP, A2A, OpenTelemetry)
- 79 relationships with no orphan nodes (`neo4j/seed_data.cypher` - 1,100+ lines)

**Testing & Validation**
- Automated test script with 10 validation cases (`scripts/test_queries.py`)
- Database initialization script (`scripts/load_sample_data.py`)
- Jupyter notebook with interactive examples (`tests/test_kg.ipynb`)
  - 12 sections of basic Cypher queries
  - Section 13: 5 `driver.execute_query()` API patterns

**Documentation**
- Complete schema definition (`docs/schema.md`)
- Project context for AI assistance (`CLAUDE.md`)
- Comprehensive README with setup instructions
- Troubleshooting guide for common issues

#### Data Quality Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Total Nodes | 67 | ✅ |
| Total Relationships | 79 | ✅ |
| Principle Coverage | 100% (11/11) | ✅ |
| Orphan Implementations | 0 | ✅ |
| Duplicate Relationships | 0 | ✅ |

**Node Distribution**:
- Principle: 11
- Method: 31
- Implementation: 16
- Standard: 3
- StandardVersion: 3
- Document: 3

**Relationship Distribution**:
- ADDRESSES: 43 (Method → Principle)
- IMPLEMENTS: 23 (Implementation → Method)
- PROPOSES: 3 (Document → Method)
- HAS_VERSION: 3 (StandardVersion → Standard)
- COMPLIES_WITH: 2 (Implementation → StandardVersion)
- USES: 2 (Method → Method)
- INTEGRATES_WITH: 3 (Implementation → Implementation)

#### Fixed

- Data quality issues from initial seed data
  - Added 6 new Methods to cover Perception, Guardrails, and Tracing principles
  - Connected 8 orphan Implementations with IMPLEMENTS relationships
  - Eliminated duplicate relationships (reduced from 120 to 79)
- Neo4j Aura connection issues on Windows
  - Added `trust="TRUST_ALL_CERTIFICATES"` for development
  - Changed URI scheme from `neo4j+s://` to `neo4j://`
- Config loading issues by modifying `settings.py` to use `__init__` method

#### Known Limitations

- 22 out of 31 Methods lack paper references (Document nodes)
- Windows environment requires trust certificate workaround
- Korean character encoding issues in some terminal environments

---

## [0.2.0] - 2026-01-30

### Phase 2: LangGraph Agent Pipeline (Partial)

#### Added

**LangGraph 4-Node Pipeline** (`src/agents/`)
- Intent Classifier node (`src/agents/nodes/intent_classifier.py`)
- Search Planner node with 7 Cypher query templates (`src/agents/nodes/search_planner.py`)
- Graph Retriever node with Neo4j result serialization (`src/agents/nodes/graph_retriever.py`)
- Synthesizer node for natural language answer generation (`src/agents/nodes/synthesizer.py`)

**Agent State Management** (`src/agents/state.py`)
- `AgentState` TypedDict with 11 fields covering intent, search strategy, results, and error handling

**Pipeline Orchestration** (`src/agents/graph.py`)
- `create_agent_graph()`: Builds compiled LangGraph StateGraph with linear flow
- `run_agent(query)`: Convenience function for single-query execution

**Testing & Documentation**
- CLI test script with 11 test queries across all intent types (`scripts/test_agent.py`)
- Comprehensive agent README with architecture, usage, and debugging guide (`src/agents/README.md`)

#### Query Intent Types Supported
| Intent | Description | Example |
|--------|-------------|---------|
| lookup | Single entity information | "What is ReAct?" |
| path | Relationship traversal | "What methods address Planning?" |
| comparison | Compare two entities | "Compare LangChain and CrewAI" |
| expansion | Web search (placeholder) | "Latest agent frameworks in 2025?" |

#### Design Decisions
- **Linear pipeline**: Sequential flow without conditional routing (branching planned for later)
- **Confidence scoring**: Based on result count adjusted by intent type
- **Result serialization**: Neo4j Node/Relationship objects converted to JSON-compatible dicts

#### Known Limitations
- Expansion intent returns placeholder message (web search requires Phase 3)
- No conversation history between queries
- No conditional routing (linear only)
- `synthesizer.py:94` — `ssl_cert_file` is loaded unconditionally; needs conditional logic or try-except since it's not mandatory in all environments
- `intent_classifier.py`, `synthesizer.py` — LLM client is hardcoded to Anthropic (`intent_classifier.py:71,73`, `synthesizer.py:98,100`) and model is pinned to `claude-3-5-sonnet` (`intent_classifier.py:76`, `synthesizer.py:103`); needs abstraction with conditional logic to support configurable providers and models
- `synthesizer.py:228-244` — Confidence thresholds (`0.9/0.8/0.7/0.5`) and intent multipliers (`*0.9/*0.8`) are hardcoded magic numbers; should be externalized to config
- `intent_classifier.py:133-142` — Fallback keyword lists for intent classification are hardcoded; not extensible without code changes
- `intent_classifier.py:151-162`, `search_planner.py:152-153,185-186` — Known entity lists are duplicated across files and disconnected from actual KG data; should be derived from graph schema or consolidated into a shared registry
- `search_planner.py:18-76` — Cypher LIMIT values are inconsistent (`10/20/30`) with no configuration

#### Remaining Phase 2 Items
- [ ] Vector search integration
- [ ] FastAPI REST endpoints
- [ ] Streamlit UI

---

## [Unreleased]

### Phase 3: Expansion (Planned)
- [ ] Web Search Expander agent
- [ ] User approval workflow UI
- [ ] Graph visualization

### Phase 4: Critic Agent (Planned)
- [ ] Evaluation principles and methods
- [ ] Evaluation logic implementation
- [ ] Guideline versioning system

### Phase 5: Prompt Optimizer (Planned)
- [ ] Failure Analyzer
- [ ] Variant Generator
- [ ] Test Runner with Critic integration

### Phase 6: Advanced Features (Planned)
- [ ] Advanced RAG techniques
- [ ] Automated data collection
- [ ] Performance optimization

---

[0.1.0]: https://github.com/yourusername/agentic-kg-explorer/releases/tag/v0.1.0
