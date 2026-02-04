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
- [x] FastAPI REST endpoints *(see v0.3.0)*
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
- ~~Embedding model hardcoded to OpenAI `text-embedding-3-small`~~ → **Fixed in v0.4.1** (YAML-driven provider pattern)
- ChromaDB telemetry warnings (`capture() takes 1 positional argument`) are harmless
- ~~No incremental embedding update~~ → **Fixed in v0.4.1** (hash-based change detection)

### FastAPI REST Endpoints

#### Added

**API Module** (`src/api/`)
- `app.py` — FastAPI app factory with lifespan context manager
- `routes.py` — 4 route handlers
- `schemas.py` — Pydantic request/response models (QueryRequest, QueryResponse, HealthResponse, StatsResponse, PrinciplesResponse)

**Endpoints**:
- `POST /query` — Run agent pipeline, returns answer + intent + sources + vector results. Supports `llm_provider`/`llm_model` override.
- `GET /health` — Neo4j connectivity + ChromaDB entry count
- `GET /stats` — Node/relationship counts by label/type
- `GET /graph/principles` — All 11 principles with method and implementation counts

**Seed Data** (`neo4j/seed_data.cypher`)
- Added `description` field to all 16 Implementation nodes (required for vector embedding)

**Migration** (`neo4j/migrations/001_add_impl_descriptions.cypher`)
- SET description on existing Implementation nodes in live Neo4j

**Scripts**
- `scripts/run_migration.py` — Generic Cypher migration runner

#### Usage

```bash
poetry run uvicorn src.api.app:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

---

## [0.4.1] - 2026-02-03

### Vector DB Refactor & Embedding Abstraction

#### Added

**Embedding Provider Abstraction** (`src/retrieval/providers/`)
- `EmbeddingProvider` abstract base class in `base.py`
- `OpenAIEmbeddingProvider` implementation in `openai.py`
- YAML-driven provider router in `router.py`
- Configure via `EMBEDDING_PROVIDER` and `EMBEDDING_MODEL` env vars
- Backward compatible: `get_embedding_client()` still works

**Incremental Embedding Updates** (`scripts/generate_embeddings.py`)
- Hash-based change detection (`data/embedding_hashes.json`)
- `--reset` flag for full rebuild (clears collection and hashes)
- `--dry-run` flag to preview changes without embedding
- Only re-embeds changed nodes (cost saving)

**Web Results Persistence** (`src/agents/nodes/web_search.py`)
- Web search results now persisted to ChromaDB
- ID format: `web:{url_hash}:{chunk_index}`
- Metadata includes `search_query` for tracking

#### Changed

**Unified Node Text with Relationship Context** (`scripts/generate_embeddings.py`)
- Complete rewrite: nodes now embedded as unified text with relationship context
- Cypher queries fetch ADDRESSES, IMPLEMENTS relationships for richer context
- Text includes: name, description, family/type, principles addressed, implementations
- ID schema changed: `kg:{node_id}` (was `{node_id}:{field}`)

**Extended Metadata Schema** (all vector entries)
- `source_type`: `kg_node` | `web_search` | `paper`
- `source_id`: node_id for KG, URL hash for web
- `source_url`: URL for web results
- `collected_at`: ISO timestamp
- `collector`: script/agent that created entry
- `node_id`, `node_label`: KG linkage
- `title`, `chunk_index`, `total_chunks`

**Vector Store Updates** (`src/retrieval/vector_store.py`)
- New collection: `kg_nodes_v2` (migration from old schema)
- `VectorSearchResult` dataclass updated for unified schema
- Added `reset()`, `delete_by_prefix()`, `upsert()` methods
- Metadata filtering support in `query()`

**API Schema Updates** (`src/api/schemas.py`)
- `VectorResultItem` updated with unified fields

**Config** (`config/providers.yaml`)
- Added `embedding_providers` section
- OpenAI embedding provider with SSL support

#### Migration

Run to regenerate embeddings with new schema:
```bash
poetry run python scripts/generate_embeddings.py --reset
```

---

## [0.4.0] - 2026-02-03

### Phase 3: Web Search Expander

#### Added

**Web Search Node** (`src/agents/nodes/web_search.py`)
- Tavily API integration for web search fallback
- Triggers on `expansion` intent OR empty KG/vector results
- Returns top 5 results with title, URL, content, score

**Conditional Pipeline Flow** (`src/agents/graph.py`)
- Changed from linear to conditional after `retrieve_from_graph`
- `_should_web_search()` routing function
- Web search node only runs when needed (cost saving)

**State Extension** (`src/agents/state.py`)
- Added `web_results: Optional[list[dict]]` — Tavily search results
- Added `web_query: Optional[str]` — query sent to Tavily

**Synthesizer Updates** (`src/agents/nodes/synthesizer.py`)
- `_format_web_results()` for LLM prompt inclusion
- `_extract_web_sources()` for source attribution
- Sources now include both KG and Web sources (type: "Web")
- Confidence base 0.5 for web-only results

**API Updates** (`src/api/`)
- `WebResultItem` schema: title, url, content, score
- `QueryResponse` extended: `web_results`, `web_query` fields
- Routes updated to map web results to response

**Dependencies**
- Added `tavily-python = "^0.5.0"` to `pyproject.toml`

#### Architecture

```
classify_intent → plan_search → retrieve_from_graph
                                        ↓
                              [conditional: has results?]
                                   ↓            ↓
                                 YES           NO (or expansion)
                                   ↓            ↓
                                 skip      web_search
                                   ↓            ↓
                                   └────────────┘
                                         ↓
                                  synthesize_answer
```

#### Usage

```bash
# Requires TAVILY_API_KEY in .env
poetry run python scripts/test_agent.py --query "What are the latest agent frameworks in 2026?"
```

#### Graceful Fallback
- If `TAVILY_API_KEY` not set → web search skipped, returns KG/vector results only
- If all sources empty → returns "couldn't find information" message

---

## [Unreleased]

### P0 Fixes: Confidence & Intent Redesign (In Progress)

#### Added

**Entity Catalog System** (`scripts/generate_entity_catalog.py`)
- Extracts all entities from Neo4j → `data/entity_catalog.json`
- Includes: principles, methods, implementations, standards
- Builds alias map (CoT → m:cot, RAG → m:rag, etc.)
- Used by intent classifier for dynamic entity context

**`out_of_scope` Intent** (`src/agents/nodes/intent_classifier.py`, `src/agents/state.py`)
- New intent type for queries outside Agentic AI domain
- Examples: "What's the weather?", "Tell me a joke"
- Returns polite rejection message, confidence=0.0

#### Changed

**Intent Classifier Redesign** (`src/agents/nodes/intent_classifier.py`)
- Loads entity catalog dynamically into prompt
- Prompt now shows actual KG entities (not hardcoded list)
- Added `_normalize_entities()` to map aliases → canonical IDs
- Fallback extraction now uses catalog when available
- 5 intents: lookup, path, comparison, expansion, out_of_scope

**Confidence Calculation Redesign** (`src/agents/nodes/synthesizer.py`)
- **OLD**: Count-based (5+ results = 0.9, etc.) — BROKEN
- **NEW**: Multi-dimensional weighted scoring:
  - Entity match (0.3): Did we find requested entities?
  - Intent fulfillment (0.3): Does result structure match intent?
  - Data completeness (0.2): Are key fields populated?
  - Vector similarity (0.2): Semantic relevance score
- New helper functions: `_calc_entity_match_score()`, `_calc_intent_fulfillment_score()`, `_calc_completeness_score()`, `_calc_vector_similarity_score()`

**State Schema** (`src/agents/state.py`)
- Added `out_of_scope` to intent Literal type

#### Verified
- [x] Entity catalog generated: 11 principles, 33 methods, 16 implementations, 3 standards, 92 aliases
- [x] Intent classification: lookup, comparison, expansion, out_of_scope all working
- [x] Confidence scoring: ReAct lookup=0.96, comparison=0.90, expansion=0.69, out_of_scope=0.0
- [x] Entity normalization: "LangChain" → `impl:langchain`, "ReAct" → `m:react`

---

### P1 Fixes: YAML Externalization & UI Improvements ✅

#### Added

**Intent Configuration** (`config/intents.yaml`)
- 11 intent types: lookup, exploration, path_trace, aggregation, comparison, recommendation, coverage_check, definition, update, expansion, out_of_scope
- Each intent has: description, examples, entity_count
- Backward compatibility aliases (path → exploration)

**Cypher Templates Configuration** (`config/cypher_templates.yaml`)
- Entity type detection patterns (Principle, Implementation, Method, Standard)
- 20+ Cypher templates organized by intent
- New templates: lookup_standard, path_trace_*, comparison_methods, comparison_principles, aggregation_*, coverage_check_*, definition_*
- Default template fallbacks per intent

#### Changed

**Search Planner** (`src/agents/nodes/search_planner.py`)
- Loads templates from YAML instead of hardcoded dict
- `_load_config()`: Lazy-loads YAML config
- `_detect_entity_type()`: Uses config patterns
- `_select_template()`: Matches intent + entity types to template
- Supports new intents: exploration, path_trace, aggregation, coverage_check, definition

**Intent Classifier** (`src/agents/nodes/intent_classifier.py`)
- Loads intent definitions from `config/intents.yaml`
- `_load_intents_config()`: Lazy-loads YAML config
- `_build_intent_list()`: Builds prompt dynamically from config
- `_extract_intent()`: Supports all config-defined intents
- Updated fallback heuristics for new intents (aggregation, coverage_check, definition)

**Agent State** (`src/agents/state.py`)
- Intent type changed from Literal to `str` to support dynamic intents from config

**Streamlit UI** (`src/ui/app.py`)
- Example query buttons now auto-execute (not just add to chat)
- Web results in collapsible expander with smaller font
- "Add to KG" panel moved to bottom in expander
- Custom CSS for compact web result display

#### Verified
- Aggregation: "How many methods address each principle?" → 11 results
- Coverage check: "Which methods are missing paper references?" → 29 results
- New intents working with YAML-driven prompt and templates

### Phase 3b: Expansion ✅ Complete
- [x] User approval workflow UI for adding web results to KG
- [x] Graph visualization with streamlit-agraph

#### Added

**Graph Visualization** (`src/ui/app.py`)
- Interactive knowledge graph visualization using `streamlit-agraph`
- Sidebar toggle to show/hide graph view
- Two view modes: "Overview (P→M→I)" and "From Last Query"
- Node colors by type (Principle=red, Method=teal, Implementation=blue, Standard=green)
- Configurable max nodes slider (10-100)
- Legend and node count display

**Helper Functions**
- `fetch_kg_subgraph()`: Fetches graph data from Neo4j (overview or centered on entity)
- `build_graph_from_results()`: Builds graph nodes/edges from query results

**Dependencies**
- Added `streamlit-agraph` to `pyproject.toml`

#### Fixed
- Graph visualization now works correctly — added `_serialize_neo4j_results()` helper to convert raw Neo4j Node/Relationship objects to plain dicts before rendering

### Phase 4: Critic Agent ✅ Implemented

#### Added

**Evaluation Schema** (`neo4j/schema.cypher`)
- EvaluationCriteria, Evaluation constraints and indexes
- FailurePattern, PromptVersion schema (Phase 5 preparation)
- DERIVED_FROM relationship (EvaluationCriteria → Principle)

**Critic Module** (`src/critic/`)
- `criteria.py` — Load evaluation criteria from YAML, caching, settings
- `scorer.py` — LLM-based scoring with rubrics, heuristic fallback
- `evaluator.py` — CriticEvaluator class with `evaluate()`, `evaluate_pipeline()`, `save_to_neo4j()`
- `__init__.py` — Module exports

**Evaluation Criteria Configuration** (`config/evaluation_criteria.yaml`)
- 15 criteria derived from 11 Principles:
  - Synthesizer (7): answer-relevance, source-citation, factual-accuracy, reasoning-steps, completeness, conciseness, safety
  - Intent Classifier (3): intent-accuracy, entity-extraction, scope-detection
  - Search Planner (3): template-selection, retrieval-mode, parameter-binding
  - Graph Retriever (2): query-execution, result-relevance
- Scoring rubrics with 0.0-1.0 scale
- Configurable weights per criterion

**Seed Data** (`neo4j/seed_evaluation.cypher`)
- MERGE statements for 15 EvaluationCriteria nodes
- Creates DERIVED_FROM relationships to Principles

**Pipeline Integration** (`src/agents/graph.py`)
- Added `evaluate: bool = False` parameter to `run_agent()`
- Post-pipeline evaluation hook (non-blocking)
- `_run_evaluation()` helper function

**API Endpoints** (`src/api/routes.py`)
- `GET /evaluations` — Query evaluation results (filter by agent, min_score, limit)
- `GET /evaluation-criteria` — List all criteria (filter by agent)

**Streamlit UI** (`src/ui/app.py`)
- "Enable Critic Evaluation" toggle in sidebar
- Evaluation scores displayed in response expander
- Per-criterion score breakdown
- Color-coded composite scores (green/orange/red)

**Scripts**
- `scripts/seed_evaluation_criteria.py` — Seed EvaluationCriteria to Neo4j

#### Architecture

```
Pipeline Execution → synthesize_answer
                            ↓
                    [if evaluate=True]
                            ↓
                    CriticEvaluator.evaluate_pipeline()
                            ↓
                    [for each agent: synthesizer, intent_classifier,
                     search_planner, graph_retriever]
                            ↓
                    score_criterion() → composite_score
                            ↓
                    [optional: save_to_neo4j()]
```

### Phase 4 + P2: Document Pipeline ✅ Implemented

#### Added

**Document Ingestion Module** (`src/ingestion/`)
- `crawler.py` — DocumentCrawler for URL and PDF extraction
  - `crawl_url()`: BeautifulSoup-based web scraping
  - `crawl_pdf()`: PyMuPDF text extraction
  - Auto-detection of doc_type (paper, article, documentation)
  - Year and author extraction heuristics
- `chunker.py` — DocumentChunker for embedding
  - Paragraph and sentence-based chunking
  - Configurable chunk_size, overlap, min_chunk_size
  - Chunk dataclass with metadata
- `linker.py` — DocumentLinker for KG relationship extraction
  - LLM-based entity extraction (Methods, Implementations mentioned)
  - Relationship types: PROPOSES, EVALUATES, DESCRIBES, USES, MENTIONS
  - Heuristic fallback when LLM unavailable
  - `save_document_to_kg()` for Neo4j persistence

**CLI Script** (`scripts/ingest_document.py`)
- `--url URL` or `--pdf PATH` input
- `--approve-all` for batch processing
- `--dry-run` preview mode
- `--embed` for ChromaDB chunk embedding
- Interactive link approval

**Streamlit Upload UI** (`src/ui/app.py`)
- "Add Document" expander in sidebar
- PDF upload and URL input tabs
- Document processing panel showing:
  - Crawl results (title, type, content length)
  - Proposed KG links with checkboxes
  - Confidence scores
- "Save to KG" with optional embedding

**Dependencies** (`pyproject.toml`)
- Added `beautifulsoup4 = "^4.12.0"` for URL crawling

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
