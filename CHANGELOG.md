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

**Multi-Provider LLM Abstraction** (`src/agents/providers/`)
- Abstract `LLMProvider` base class (`base.py`)
- Provider router with primary/fallback chain (`router.py`)
- OpenAI provider — default model: `gpt-4o-mini` (`openai.py`)
- Anthropic provider — default model: `claude-3-5-sonnet-20241022` (`anthropic.py`)
- Gemini provider — default model: `gemini-2.5-flash` (`gemini.py`)
- SSL certificate handling per provider (conditional, macOS/Windows/WSL compatible)
- Configuration via `.env`: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_FALLBACK_PROVIDER`

**Agent State Management** (`src/agents/state.py`)
- `AgentState` TypedDict with 11 fields covering intent, search strategy, results, and error handling

**Pipeline Orchestration** (`src/agents/graph.py`)
- `create_agent_graph()`: Builds compiled LangGraph StateGraph with linear flow
- `run_agent(query)`: Convenience function for single-query execution

**Configuration Management** (`config/settings.py`)
- Pydantic Settings with dotenv integration
- Provider selection, model override, token limits, fallback provider settings
- API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`

**Testing & Documentation**
- CLI test script with 11 test queries across all intent types (`scripts/test_agent.py`)
- Provider/model override via CLI: `--llm-provider`, `--llm-model`
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
- **Provider abstraction**: Simple `generate(prompt, max_tokens) -> str` interface; no LangChain LLM wrappers used for provider calls
- **Fallback chain**: Primary provider → fallback provider → heuristic (keyword-based)
- **Confidence scoring**: Based on result count adjusted by intent type
- **Result serialization**: Neo4j Node/Relationship objects converted to JSON-compatible dicts

#### Fixed (from v0.2.0-pre)
- LLM client no longer hardcoded to Anthropic; uses configurable provider router
- SSL cert loading is now conditional (only when `SSL_CERT_FILE` env var is set and file exists)

#### Known Limitations
- Expansion intent returns placeholder message (web search requires Phase 3)
- No conversation history between queries
- No conditional routing (linear only)
- Confidence thresholds (`0.9/0.8/0.7/0.5`) and intent multipliers hardcoded
- Fallback keyword lists for intent classification are hardcoded
- Known entity lists duplicated across files; should be derived from graph schema
- Cypher LIMIT values inconsistent (`10/20/30`) with no configuration
- `gemini-1.5-flash` model deprecated in Google AI API; use `gemini-2.0-flash` or later

#### Remaining Phase 2 Items
- [ ] **Provider config externalization**: Replace per-provider install/uninstall cycle with declarative config (e.g. YAML) where only `provider: gemini` is needed — router auto-resolves SDK, defaults, SSL. Current approach requires touching `router.py`, `settings.py`, and `pyproject.toml` for every provider change; a config-driven approach would decouple provider selection from code. Scope: `config/`, `src/agents/providers/`, `pyproject.toml` optional-deps grouping.
- [x] Vector search integration *(see v0.3.0)*
- [ ] FastAPI REST endpoints
- [ ] Streamlit UI

---

## [0.3.0] - 2026-01-31

### Vector Search Integration (ChromaDB)

#### Added

**Retrieval Module** (`src/retrieval/`)
- `EmbeddingClient` wrapping OpenAI `text-embedding-3-small` with SSL-aware httpx client (`embedder.py`)
- `VectorStore` wrapping ChromaDB `PersistentClient` with cosine HNSW index (`vector_store.py`)
- `VectorSearchResult` dataclass: `node_id`, `node_label`, `text`, `field`, `score`
- Module exports in `__init__.py`: `EmbeddingClient`, `VectorStore`, `VectorSearchResult`, factory functions

**Embedding Generation Script** (`scripts/generate_embeddings.py`)
- Fetches Method, Principle, Document, Implementation nodes from Neo4j
- Embeds `name`, `description`, `title`, `abstract` fields via OpenAI batched API
- Upserts into ChromaDB with metadata `{node_id, node_label, field}`
- ID format: `"{node_id}:{field}"` (e.g., `"m:react:description"`)

**Three-Mode Retrieval in Agent Pipeline**
- `graph_only`: existing Cypher behavior (unchanged)
- `vector_first`: embed query → ChromaDB similarity → enrich from Neo4j
- `hybrid`: Cypher + ChromaDB → merge results, confidence boost on overlap

#### Changed

**`src/agents/state.py`**
- Added `vector_results: Optional[list[dict]]` field to `AgentState`

**`src/agents/graph.py`**
- Initialized `vector_results: None` in `run_agent()` initial state

**`src/agents/nodes/search_planner.py`**
- Added `_maybe_add_vector_search()` strategy selector:
  - `expansion` intent → `vector_first`
  - No Cypher template → `vector_first`
  - `lookup`/`path` with recognized entities → `hybrid`
  - Otherwise → `graph_only` (unchanged)
- Sets `strategy["vector_query"]` for downstream vector search

**`src/agents/nodes/graph_retriever.py`**
- Added `_run_vector_search()`: embed query via OpenAI, query ChromaDB, return serialized results
- Added `_enrich_from_neo4j()`: fetch full node data + connections for vector-matched node IDs
- Main `retrieve_from_graph()` now handles all three retrieval types

**`src/agents/nodes/synthesizer.py`**
- Added `_format_vector_results()`: formats semantic search results for LLM prompt
- Prompt template now includes `{vector_section}` placeholder
- `_calculate_confidence()` updated: confidence boost (+0.05) when graph and vector results overlap; base 0.55 for vector-only results

**`pyproject.toml`**
- Added `chromadb = ">=0.5.0,<1.0.0"`

**`.gitignore`**
- Added `data/chroma/` (binary index files)

#### Architecture

```
User Query
    ↓
[Intent Classifier]  (unchanged)
    ↓
[Search Planner]     → decides: graph_only | vector_first | hybrid
    ↓
[Graph Retriever]    → executes Cypher AND/OR ChromaDB query
    ↓
[Synthesizer]        → includes vector results in prompt
```

#### Usage

```bash
# 1. Install dependencies
poetry install

# 2. Generate embeddings (requires OPENAI_API_KEY)
poetry run python scripts/generate_embeddings.py

# 3. Test with queries
poetry run python scripts/test_agent.py --query "reasoning and acting loop"  # vector_first
poetry run python scripts/test_agent.py --query "What is ReAct?"             # hybrid
```

#### Graceful Fallback
- If `data/chroma/` is missing or empty → `is_available = False` → all queries fall back to `graph_only`
- If `OPENAI_API_KEY` is not set → `get_embedding_client()` returns `None` → vector search skipped

#### Known Limitations
- Embedding model hardcoded to OpenAI `text-embedding-3-small`; should follow YAML-driven provider pattern in future
- ChromaDB telemetry warnings (`capture() takes 1 positional argument`) are harmless
- No incremental embedding update — `generate_embeddings.py` re-embeds all nodes on each run

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
