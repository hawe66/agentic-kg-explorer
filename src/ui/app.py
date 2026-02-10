"""Streamlit UI for Agentic KG Explorer."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from config.settings import get_settings
from src.agents.graph import run_agent
from src.api.kg_writer import propose_node, approve_node, WebResult, ProposedNode
from src.graph.client import Neo4jClient


# ---------------------------------------------------------------------------
# Neo4j Serialization Helper
# ---------------------------------------------------------------------------

def _serialize_neo4j_value(value):
    """Serialize Neo4j Node/Relationship objects to plain dicts."""
    # Neo4j Node: has .labels and .items()
    if hasattr(value, "labels") and hasattr(value, "items"):
        return {
            "labels": list(value.labels),
            "properties": dict(value.items()),
            "element_id": getattr(value, "element_id", None),
        }
    # Neo4j Relationship: has .type and .items()
    elif hasattr(value, "type") and hasattr(value, "items") and hasattr(value, "start_node"):
        return {
            "type": value.type,
            "properties": dict(value.items()),
            "start_node": _serialize_neo4j_value(value.start_node),
            "end_node": _serialize_neo4j_value(value.end_node),
        }
    elif isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_serialize_neo4j_value(v) for v in value]
    else:
        return value


def _serialize_neo4j_results(results: list) -> list[dict]:
    """Serialize a list of Neo4j records to plain dicts."""
    return [
        {key: _serialize_neo4j_value(val) for key, val in record.items()}
        for record in results
    ]


st.set_page_config(
    page_title="Agentic KG Explorer",
    page_icon="🔍",
    layout="wide",
)

# Custom CSS for UI improvements
st.markdown("""
<style>
/* Smaller font for web results */
.web-result-content {
    font-size: 0.85rem;
    color: #666;
}
.web-result-title {
    font-size: 0.95rem;
    font-weight: 600;
}
/* Compact expander for Add to KG */
.stExpander {
    border: 1px solid #ddd;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("🔍 Agentic KG Explorer")
st.caption("Query the Agentic AI Knowledge Graph")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_proposal" not in st.session_state:
    st.session_state.pending_proposal = None

if "last_web_results" not in st.session_state:
    st.session_state.last_web_results = []

if "auto_submit_query" not in st.session_state:
    st.session_state.auto_submit_query = None

if "show_graph" not in st.session_state:
    st.session_state.show_graph = False

if "graph_data" not in st.session_state:
    st.session_state.graph_data = None

if "last_evaluation" not in st.session_state:
    st.session_state.last_evaluation = None

if "pending_document" not in st.session_state:
    st.session_state.pending_document = None

if "document_links" not in st.session_state:
    st.session_state.document_links = None

if "last_kg_results" not in st.session_state:
    st.session_state.last_kg_results = None

# Optimizer state
if "optimizer_patterns" not in st.session_state:
    st.session_state.optimizer_patterns = []

if "optimizer_selected_pattern" not in st.session_state:
    st.session_state.optimizer_selected_pattern = None

if "optimizer_edited_hypotheses" not in st.session_state:
    st.session_state.optimizer_edited_hypotheses = []

if "optimizer_variants" not in st.session_state:
    st.session_state.optimizer_variants = []

if "optimizer_test_results" not in st.session_state:
    st.session_state.optimizer_test_results = []

if "optimizer_gate" not in st.session_state:
    st.session_state.optimizer_gate = None  # None | "gate1" | "gate2"

if "optimizer_show_history" not in st.session_state:
    st.session_state.optimizer_show_history = False


# ---------------------------------------------------------------------------
# Graph Visualization Helpers
# ---------------------------------------------------------------------------

# Node colors by type
NODE_COLORS = {
    "Principle": "#FF6B6B",      # Red
    "Method": "#4ECDC4",         # Teal
    "Implementation": "#45B7D1", # Blue
    "Standard": "#96CEB4",       # Green
    "StandardVersion": "#BFCBA8",
    "Document": "#DDA0DD",       # Plum
}

def _extract_node_ids(kg_results: list[dict]) -> list[str]:
    """Extract unique node IDs from serialized kg_results."""
    ids = set()
    for record in kg_results:
        for key, value in record.items():
            _collect_ids(value, ids)
    return list(ids)


def _collect_ids(value, ids: set):
    """Recursively collect node IDs from nested structures."""
    if isinstance(value, dict):
        if "labels" in value and "properties" in value:
            node_id = value["properties"].get("id")
            if node_id:
                ids.add(node_id)
        else:
            for v in value.values():
                _collect_ids(v, ids)
    elif isinstance(value, list):
        for item in value:
            _collect_ids(item, ids)


def fetch_kg_subgraph_for_ids(node_ids: list[str], max_nodes: int = 50) -> tuple[list, list]:
    """Fetch subgraph containing the given node IDs and their mutual relationships."""
    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    if not node_ids:
        return nodes, edges

    try:
        with Neo4jClient() as client:
            query = """
            MATCH (n) WHERE n.id IN $ids
            OPTIONAL MATCH (n)-[r]-(m) WHERE m.id IN $ids
            RETURN n, r, m
            """
            raw_results = client.run_cypher(query, {"ids": node_ids[:max_nodes]})
            results = _serialize_neo4j_results(raw_results)

            for record in results:
                for key, value in record.items():
                    if value is None:
                        continue

                    if isinstance(value, dict) and "labels" in value:
                        props = value.get("properties", {})
                        node_id = props.get("id", "")
                        if node_id and node_id not in seen_nodes:
                            label = value["labels"][0] if value["labels"] else "Unknown"
                            nodes.append(Node(
                                id=node_id,
                                label=props.get("name", node_id)[:20],
                                size=25 if label == "Principle" else 20,
                                color=NODE_COLORS.get(label, "#888888"),
                                title=f"{label}: {props.get('name', node_id)}\n{props.get('description', '')[:100]}..."
                            ))
                            seen_nodes.add(node_id)

                    elif isinstance(value, dict) and "type" in value and "start_node" in value:
                        rel_type = value.get("type", "")
                        start_props = value.get("start_node", {}).get("properties", {})
                        end_props = value.get("end_node", {}).get("properties", {})
                        start_id = start_props.get("id")
                        end_id = end_props.get("id")
                        if start_id and end_id:
                            edge_key = (start_id, end_id, rel_type)
                            if edge_key not in seen_edges:
                                edges.append(Edge(
                                    source=start_id,
                                    target=end_id,
                                    label=rel_type[:10],
                                    color="#888888"
                                ))
                                seen_edges.add(edge_key)

    except Exception as e:
        st.error(f"Failed to fetch query subgraph: {e}")

    return nodes[:max_nodes], edges


def fetch_kg_subgraph(center_id: str = None, max_nodes: int = 50) -> tuple[list, list]:
    """Fetch a subgraph from Neo4j centered on an entity or overview."""
    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    try:
        with Neo4jClient() as client:
            if center_id:
                # Fetch neighborhood of specific node
                query = """
                MATCH (n)
                WHERE n.id = $center_id
                OPTIONAL MATCH (n)-[r]-(m)
                RETURN n, r, m
                LIMIT 100
                """
                raw_results = client.run_cypher(query, {"center_id": center_id})
            else:
                # Fetch overview: Principles -> Methods -> Implementations
                query = """
                MATCH (p:Principle)<-[a:ADDRESSES]-(m:Method)
                OPTIONAL MATCH (m)<-[i:IMPLEMENTS]-(impl:Implementation)
                RETURN p, a, m, i, impl
                LIMIT 200
                """
                raw_results = client.run_cypher(query)

            # Serialize Neo4j objects to plain dicts
            results = _serialize_neo4j_results(raw_results)

            for record in results:
                for key, value in record.items():
                    if value is None:
                        continue

                    # Handle nodes (serialized format has "labels" key)
                    if isinstance(value, dict) and "labels" in value:
                        props = value.get("properties", {})
                        node_id = props.get("id", "")
                        if node_id and node_id not in seen_nodes:
                            label = value["labels"][0] if value["labels"] else "Unknown"
                            nodes.append(Node(
                                id=node_id,
                                label=props.get("name", node_id)[:20],
                                size=25 if label == "Principle" else 20,
                                color=NODE_COLORS.get(label, "#888888"),
                                title=f"{label}: {props.get('name', node_id)}\n{props.get('description', '')[:100]}..."
                            ))
                            seen_nodes.add(node_id)

                    # Handle relationships (serialized format has "type" and "start_node"/"end_node")
                    elif isinstance(value, dict) and "type" in value and "start_node" in value:
                        rel_type = value.get("type", "")
                        start_props = value.get("start_node", {}).get("properties", {})
                        end_props = value.get("end_node", {}).get("properties", {})
                        start_id = start_props.get("id")
                        end_id = end_props.get("id")
                        if start_id and end_id:
                            edge_key = (start_id, end_id, rel_type)
                            if edge_key not in seen_edges:
                                edges.append(Edge(
                                    source=start_id,
                                    target=end_id,
                                    label=rel_type[:10],
                                    color="#888888"
                                ))
                                seen_edges.add(edge_key)

    except Exception as e:
        st.error(f"Failed to fetch graph: {e}")

    return nodes[:max_nodes], edges


def build_graph_from_results(kg_results: list) -> tuple[list, list]:
    """Build graph nodes and edges from query results."""
    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    for record in kg_results:
        for key, value in record.items():
            if value is None:
                continue

            # Handle single node
            if isinstance(value, dict) and "labels" in value:
                props = value.get("properties", {})
                node_id = props.get("id", "")
                if node_id and node_id not in seen_nodes:
                    label = value["labels"][0] if value["labels"] else "Unknown"
                    nodes.append(Node(
                        id=node_id,
                        label=props.get("name", node_id)[:25],
                        size=30 if label == "Principle" else 25 if label == "Method" else 20,
                        color=NODE_COLORS.get(label, "#888888"),
                        title=f"{label}: {props.get('name', node_id)}"
                    ))
                    seen_nodes.add(node_id)

            # Handle list of nodes/relationships
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # Nested structure like {method: {...}, support_level: ...}
                        for sub_key, sub_val in item.items():
                            if isinstance(sub_val, dict) and "labels" in sub_val:
                                props = sub_val.get("properties", {})
                                node_id = props.get("id", "")
                                if node_id and node_id not in seen_nodes:
                                    label = sub_val["labels"][0] if sub_val["labels"] else "Unknown"
                                    nodes.append(Node(
                                        id=node_id,
                                        label=props.get("name", node_id)[:25],
                                        size=25,
                                        color=NODE_COLORS.get(label, "#888888"),
                                        title=f"{label}: {props.get('name', node_id)}"
                                    ))
                                    seen_nodes.add(node_id)

    # Infer edges from relationships in data
    # (simplified - connect methods to principles, implementations to methods)
    node_ids = list(seen_nodes)
    for i, n1 in enumerate(node_ids):
        for n2 in node_ids[i+1:]:
            # Connect based on prefix patterns
            if (n1.startswith("p:") and n2.startswith("m:")) or (n2.startswith("p:") and n1.startswith("m:")):
                edge_key = tuple(sorted([n1, n2]))
                if edge_key not in seen_edges:
                    edges.append(Edge(source=n1, target=n2, color="#cccccc"))
                    seen_edges.add(edge_key)
            elif (n1.startswith("m:") and n2.startswith("impl:")) or (n2.startswith("m:") and n1.startswith("impl:")):
                edge_key = tuple(sorted([n1, n2]))
                if edge_key not in seen_edges:
                    edges.append(Edge(source=n1, target=n2, color="#cccccc"))
                    seen_edges.add(edge_key)

    return nodes, edges


# ---------------------------------------------------------------------------
# Sidebar - Provider/Model Selection
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("LLM Settings")

    providers = ["openai", "anthropic", "gemini"]
    provider_models = {
        "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "gemini": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    }

    selected_provider = st.selectbox(
        "Provider",
        providers,
        index=0,
        help="Select the LLM provider",
    )

    selected_model = st.selectbox(
        "Model",
        provider_models.get(selected_provider, []),
        index=0,
        help="Select the model to use",
    )

    st.divider()

    st.header("About")
    st.write(
        "This app explores an Agentic AI knowledge graph containing "
        "methods, implementations, principles, and research papers."
    )

    st.divider()

    st.header("Example Queries")
    examples = [
        "What is ReAct?",
        "What methods address Planning?",
        "Compare LangChain and CrewAI",
        "How many methods address each principle?",
        "What are the latest AI agent frameworks?",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            # Set auto-submit flag to trigger agent on next rerun
            st.session_state.auto_submit_query = ex
            st.rerun()

    st.divider()

    st.header("Graph View")
    if st.toggle("Show Knowledge Graph", value=st.session_state.show_graph, key="graph_toggle"):
        st.session_state.show_graph = True
    else:
        st.session_state.show_graph = False

    st.divider()

    st.header("Evaluation")
    enable_evaluation = st.toggle(
        "Enable Critic Evaluation",
        value=False,
        help="Run evaluation on agent outputs after each query (Phase 4)",
        key="eval_toggle"
    )

    st.divider()

    # Document Upload Section
    st.header("Add Document")
    with st.expander("📄 Upload Document", expanded=False):
        upload_tab, url_tab = st.tabs(["PDF Upload", "URL"])

        with upload_tab:
            uploaded_file = st.file_uploader(
                "Choose PDF",
                type=["pdf"],
                help="Upload a PDF document to analyze and link to KG"
            )
            if uploaded_file and st.button("Process PDF", key="process_pdf"):
                st.session_state.pending_document = {
                    "type": "pdf",
                    "file": uploaded_file,
                }
                st.rerun()

        with url_tab:
            doc_url = st.text_input(
                "Document URL",
                placeholder="https://example.com/article",
                help="Enter URL of article or paper to analyze"
            )
            if doc_url and st.button("Process URL", key="process_url"):
                st.session_state.pending_document = {
                    "type": "url",
                    "url": doc_url,
                }
                st.rerun()

    st.divider()

    # Prompt Optimizer Section
    st.header("Prompt Optimizer")
    with st.expander("🔧 Failure Patterns", expanded=False):
        # Analyze button
        if st.button("Analyze Failures", key="analyze_failures"):
            with st.spinner("Analyzing evaluations..."):
                try:
                    from src.optimizer import FailureAnalyzer
                    analyzer = FailureAnalyzer(threshold=0.6)
                    patterns = analyzer.analyze()
                    st.session_state.optimizer_patterns = patterns
                    if patterns:
                        st.success(f"Found {len(patterns)} failure pattern(s)")
                    else:
                        st.info("No failure patterns detected")
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

        # Show patterns
        if st.session_state.optimizer_patterns:
            for i, pattern in enumerate(st.session_state.optimizer_patterns):
                score_color = "green" if pattern.avg_score >= 0.7 else "orange" if pattern.avg_score >= 0.5 else "red"
                st.markdown(
                    f"**{pattern.agent_name}** / {pattern.criterion_id.split(':')[-1]}  \n"
                    f"Freq: {pattern.frequency} | "
                    f"<span style='color:{score_color}'>Avg: {pattern.avg_score:.2f}</span>",
                    unsafe_allow_html=True
                )
                if st.button("Start Optimization", key=f"opt_pattern_{i}"):
                    st.session_state.optimizer_selected_pattern = pattern
                    st.session_state.optimizer_edited_hypotheses = list(pattern.root_cause_hypotheses)
                    st.session_state.optimizer_gate = "gate1"
                    st.rerun()
                st.markdown("---")

        # Version history button
        if st.button("📜 Version History", key="version_history"):
            st.session_state.optimizer_show_history = True
            st.rerun()

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.last_web_results = []
        st.session_state.last_kg_results = None
        st.session_state.pending_proposal = None
        st.session_state.graph_data = None
        st.session_state.optimizer_gate = None
        st.session_state.optimizer_selected_pattern = None
        st.session_state.optimizer_show_history = False
        st.rerun()


# ---------------------------------------------------------------------------
# Chat interface
# ---------------------------------------------------------------------------

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for src in msg["sources"]:
                    st.write(f"- [{src['type']}] {src['name']}")


# Handle auto-submit from example buttons
prompt = None
if st.session_state.auto_submit_query:
    prompt = st.session_state.auto_submit_query
    st.session_state.auto_submit_query = None

# Chat input (manual)
if manual_prompt := st.chat_input("Ask about agentic AI methods, implementations, or principles..."):
    prompt = manual_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Searching with {selected_provider}/{selected_model}..."):
            try:
                settings = get_settings()
                original_provider = settings.llm_provider
                original_model = settings.llm_model

                settings.llm_provider = selected_provider
                settings.llm_model = selected_model

                try:
                    result = run_agent(prompt, evaluate=enable_evaluation)
                finally:
                    settings.llm_provider = original_provider
                    settings.llm_model = original_model

                # Store evaluation results if available
                if enable_evaluation:
                    try:
                        from src.critic.evaluator import get_evaluator
                        evaluator = get_evaluator()
                        evaluations = evaluator.evaluate_pipeline(result)
                        st.session_state.last_evaluation = evaluations
                    except Exception as eval_err:
                        st.session_state.last_evaluation = None
                        st.warning(f"Evaluation failed: {eval_err}")

                answer = result.get("answer") or "I couldn't find relevant information."
                sources = result.get("sources") or []
                intent = result.get("intent")
                confidence = result.get("confidence")
                web_results = result.get("web_results") or []

                # Store results for visualization and "Add to KG"
                st.session_state.last_kg_results = result.get("kg_results")
                st.session_state.last_web_results = web_results

                st.markdown(answer)

                col1, col2, col3 = st.columns(3)
                with col1:
                    if intent:
                        st.caption(f"Intent: {intent}")
                with col2:
                    if confidence:
                        st.caption(f"Confidence: {confidence:.0%}")
                with col3:
                    st.caption(f"Model: {selected_model}")

                if sources:
                    with st.expander("Sources", expanded=False):
                        for src in sources:
                            src_type = src.get("type", "Unknown")
                            src_name = src.get("name", "Unknown")
                            src_url = src.get("url", "")
                            if src_url:
                                st.write(f"- [{src_type}] [{src_name}]({src_url})")
                            else:
                                st.write(f"- [{src_type}] {src_name}")

                vector_results = result.get("vector_results") or []
                if vector_results:
                    with st.expander(f"Vector Results ({len(vector_results)})", expanded=False):
                        for vr in vector_results:
                            src_type = vr.get("source_type", "unknown")
                            title = vr.get("title", "Untitled")
                            score = vr.get("score", 0)
                            st.write(f"- [{src_type}] {title} (score: {score:.2f})")

                # Show evaluation results if available
                if enable_evaluation and st.session_state.last_evaluation:
                    with st.expander(f"📊 Evaluation ({len(st.session_state.last_evaluation)} agents)", expanded=False):
                        for ev in st.session_state.last_evaluation:
                            score_pct = ev.composite_score * 100
                            score_color = "green" if score_pct >= 70 else "orange" if score_pct >= 50 else "red"
                            st.markdown(f"**{ev.agent_name}**: <span style='color:{score_color}'>{score_pct:.0f}%</span>", unsafe_allow_html=True)

                            # Show individual criterion scores
                            if ev.scores:
                                score_items = ", ".join([f"{k.split(':')[-1]}: {v:.0%}" for k, v in ev.scores.items()])
                                st.caption(score_items)

                            # Show feedback if low score
                            if ev.feedback:
                                st.caption(f"💡 {ev.feedback[:150]}...")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })


# ---------------------------------------------------------------------------
# Web Results with "Add to KG" buttons (collapsible)
# ---------------------------------------------------------------------------

if st.session_state.last_web_results:
    with st.expander(f"🌐 Web Search Results ({len(st.session_state.last_web_results)})", expanded=False):
        st.caption("Click 'Add to KG' to propose adding this content to the knowledge graph")

        for i, wr in enumerate(st.session_state.last_web_results):
            col1, col2 = st.columns([5, 1])

            with col1:
                # Smaller font for web results
                title = wr.get('title', 'Untitled')
                url = wr.get('url', '')
                content = wr.get("content", "")[:200] + "..."
                st.markdown(f"<p class='web-result-title'><a href='{url}'>{title}</a></p>", unsafe_allow_html=True)
                st.markdown(f"<p class='web-result-content'>{content}</p>", unsafe_allow_html=True)

            with col2:
                if st.button("➕ Add", key=f"add_kg_{i}", help="Add to Knowledge Graph"):
                    with st.spinner("Extracting..."):
                        web_result = WebResult(
                            title=wr.get("title", ""),
                            url=wr.get("url", ""),
                            content=wr.get("content", ""),
                        )
                        proposal = propose_node(web_result)

                        if proposal:
                            st.session_state.pending_proposal = proposal
                            st.rerun()
                        else:
                            st.error("Could not extract entity")

            if i < len(st.session_state.last_web_results) - 1:
                st.divider()


# ---------------------------------------------------------------------------
# Add to KG Panel (at bottom, in expander)
# ---------------------------------------------------------------------------

if st.session_state.pending_proposal is not None:
    proposal = st.session_state.pending_proposal

    expander_title = "📝 Update Node" if proposal.exists_in_kg else "📝 Add to Knowledge Graph"
    with st.expander(expander_title, expanded=True):
        if proposal.exists_in_kg:
            st.info("This entity already exists in KG. Review and update if needed.")
        else:
            st.info("Review the proposed node and click 'Create Node' to add to KG.")

        with st.form("approve_node_form"):
            st.write(f"**{proposal.node_type}**")

            node_id = st.text_input("Node ID", value=proposal.node_id, disabled=proposal.exists_in_kg)
            name = st.text_input("Name", value=proposal.name)

            if proposal.exists_in_kg and proposal.existing_description:
                st.caption("Current description:")
                st.text(proposal.existing_description[:150] + "..." if len(proposal.existing_description or "") > 150 else proposal.existing_description)

            description = st.text_area("Description", value=proposal.description, height=100)

            col1, col2 = st.columns(2)

            # Type-specific fields
            method_family = None
            granularity = None
            impl_type = None
            maintainer = None
            doc_type = None
            year = None

            if proposal.node_type == "Method":
                with col1:
                    method_family = st.selectbox(
                        "Method Family",
                        ["prompting_decoding", "agent_loop_pattern", "workflow_orchestration",
                         "retrieval_grounding", "memory_system", "reflection_verification",
                         "multi_agent_coordination", "training_alignment", "safety_control",
                         "evaluation", "observability_tracing"],
                    )
                with col2:
                    granularity = st.selectbox("Granularity", ["atomic", "composite"])

            elif proposal.node_type == "Implementation":
                with col1:
                    impl_type = st.selectbox("Type", ["framework", "library", "platform", "service"])
                with col2:
                    maintainer = st.text_input("Maintainer", value=proposal.maintainer or "")

            elif proposal.node_type == "Document":
                with col1:
                    doc_type = st.selectbox("Doc Type", ["paper", "article", "documentation"])
                with col2:
                    year = st.number_input("Year", value=proposal.year or 2024, min_value=1900, max_value=2030)

            st.caption(f"Source: {proposal.source_url} | Confidence: {proposal.confidence:.0%}")

            col1, col2 = st.columns(2)
            with col1:
                button_label = "✅ Update" if proposal.exists_in_kg else "✅ Create"
                submitted = st.form_submit_button(button_label, type="primary")
            with col2:
                cancelled = st.form_submit_button("❌ Cancel")

            if submitted:
                updated = ProposedNode(
                    node_type=proposal.node_type,
                    node_id=node_id,
                    name=name,
                    description=description,
                    method_family=method_family,
                    method_type=proposal.method_type,
                    granularity=granularity,
                    addresses=proposal.addresses,
                    impl_type=impl_type,
                    maintainer=maintainer,
                    source_repo=proposal.source_repo,
                    implements=proposal.implements,
                    doc_type=doc_type,
                    authors=proposal.authors,
                    year=year,
                    venue=proposal.venue,
                    proposes=proposal.proposes,
                    source_url=proposal.source_url,
                    confidence=proposal.confidence,
                    exists_in_kg=proposal.exists_in_kg,
                    existing_description=proposal.existing_description,
                )

                result = approve_node(updated, update_mode=proposal.exists_in_kg)

                if result.success:
                    action = "Updated" if proposal.exists_in_kg else "Created"
                    st.success(f"{action} node: {result.node_id}")
                    st.session_state.pending_proposal = None
                    st.rerun()
                else:
                    st.error(result.message)

            if cancelled:
                st.session_state.pending_proposal = None
                st.rerun()


# ---------------------------------------------------------------------------
# Document Processing Panel
# ---------------------------------------------------------------------------

if st.session_state.pending_document is not None:
    doc_info = st.session_state.pending_document

    with st.expander("📄 Processing Document", expanded=True):
        try:
            from src.ingestion.crawler import DocumentCrawler
            from src.ingestion.linker import DocumentLinker
            from src.ingestion.chunker import chunk_for_embedding
            import tempfile

            crawler = DocumentCrawler()
            linker = DocumentLinker()

            # Step 1: Crawl document
            with st.spinner("Crawling document..."):
                if doc_info["type"] == "pdf":
                    # Save uploaded file to temp location
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(doc_info["file"].getvalue())
                        tmp_path = tmp.name
                    doc = crawler.crawl_pdf(tmp_path)
                else:
                    doc = crawler.crawl_url(doc_info["url"])

            st.success(f"Crawled: {doc.title}")
            st.caption(f"Type: {doc.doc_type} | {len(doc.content)} chars")

            # Step 2: Extract links
            with st.spinner("Analyzing for KG links..."):
                result = linker.link_document(doc)

            if result.proposed_links:
                st.write(f"**Found {len(result.proposed_links)} proposed links:**")

                # Store for approval
                st.session_state.document_links = {
                    "doc": doc,
                    "links": result.proposed_links,
                    "approved": [True] * len(result.proposed_links),  # Default all approved
                }

                # Show links with checkboxes
                with st.form("approve_doc_links"):
                    for i, link in enumerate(result.proposed_links):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.checkbox(
                                f"{link.entity_name}",
                                value=True,
                                key=f"link_{i}",
                                help=f"{link.entity_type}: {link.entity_id}"
                            )
                        with col2:
                            st.caption(f"{link.relationship}")
                        with col3:
                            st.caption(f"{link.confidence:.0%}")

                    st.caption("Uncheck links you don't want to create")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        save_links = st.form_submit_button("✅ Save to KG", type="primary")
                    with col2:
                        embed_too = st.checkbox("Also embed chunks", value=True)
                    with col3:
                        cancel_doc = st.form_submit_button("❌ Cancel")

                    if save_links:
                        # Collect approved links
                        approved = []
                        for i, link in enumerate(result.proposed_links):
                            if st.session_state.get(f"link_{i}", True):
                                approved.append(link)

                        if approved:
                            with st.spinner("Saving to Neo4j..."):
                                success = linker.save_document_to_kg(doc, approved)

                            if success:
                                st.success(f"Saved {len(approved)} links for {doc.doc_id}")

                                # Optionally embed
                                if embed_too:
                                    with st.spinner("Generating embeddings..."):
                                        try:
                                            from src.retrieval.vector_store import get_vector_store
                                            chunks = chunk_for_embedding(doc)
                                            store = get_vector_store()

                                            ids = []
                                            documents = []
                                            metadatas = []
                                            for chunk in chunks:
                                                ids.append(f"doc:{doc.content_hash}:{chunk.chunk_index}")
                                                documents.append(chunk.text)
                                                metadatas.append({
                                                    "source_type": "document",
                                                    "source_url": doc.source_url or "",
                                                    "node_id": doc.doc_id,
                                                    "node_label": "Document",
                                                    "title": doc.title,
                                                    "chunk_index": chunk.chunk_index,
                                                    "total_chunks": chunk.total_chunks,
                                                })

                                            store.add_documents(documents, metadatas, ids)
                                            st.success(f"Embedded {len(chunks)} chunks")
                                        except Exception as e:
                                            st.warning(f"Embedding failed: {e}")

                                st.session_state.pending_document = None
                                st.session_state.document_links = None
                                st.rerun()
                            else:
                                st.error("Failed to save to Neo4j")
                        else:
                            st.warning("No links selected")

                    if cancel_doc:
                        st.session_state.pending_document = None
                        st.session_state.document_links = None
                        st.rerun()

            else:
                st.warning("No relevant KG entities found in this document")
                if st.button("Close", key="close_doc"):
                    st.session_state.pending_document = None
                    st.rerun()

        except Exception as e:
            st.error(f"Error processing document: {e}")
            if st.button("Close", key="close_doc_error"):
                st.session_state.pending_document = None
                st.rerun()


# ---------------------------------------------------------------------------
# Knowledge Graph Visualization
# ---------------------------------------------------------------------------

if st.session_state.show_graph:
    st.divider()
    st.subheader("Knowledge Graph Visualization")

    # Graph control options
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        graph_mode = st.selectbox(
            "View Mode",
            ["Overview (P→M→I)", "From Last Query"],
            help="Overview: Show Principles→Methods→Implementations structure\nFrom Query: Show nodes from your last query results"
        )
    with col2:
        max_nodes = st.slider("Max Nodes", min_value=10, max_value=100, value=40)
    with col3:
        if st.button("Refresh Graph"):
            st.session_state.graph_data = None

    # Fetch or build graph data
    nodes, edges = [], []

    if graph_mode == "From Last Query" and st.session_state.last_kg_results:
        node_ids = _extract_node_ids(st.session_state.last_kg_results)
        if node_ids:
            nodes, edges = fetch_kg_subgraph_for_ids(node_ids, max_nodes=max_nodes)
        else:
            st.info("No graph entities found in last query results.")
    elif graph_mode == "From Last Query":
        st.info("Run a query first to see its graph.")
    else:
        # Overview mode - fetch from KG
        nodes, edges = fetch_kg_subgraph(max_nodes=max_nodes)

    if nodes:
        # Configure graph layout
        config = Config(
            width="100%",
            height=500,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=False,
            node={
                "labelProperty": "label",
                "renderLabel": True,
            },
            link={
                "labelProperty": "label",
                "renderLabel": True,
            }
        )

        # Render the graph
        selected_node = agraph(nodes=nodes, edges=edges, config=config)

        # Show legend
        st.caption("Legend: ")
        legend_cols = st.columns(len(NODE_COLORS))
        for i, (node_type, color) in enumerate(NODE_COLORS.items()):
            with legend_cols[i]:
                st.markdown(f"<span style='color:{color}'>●</span> {node_type}", unsafe_allow_html=True)

        # Show node details if selected
        if selected_node:
            st.info(f"Selected: {selected_node}")

        st.caption(f"Showing {len(nodes)} nodes, {len(edges)} edges")
    else:
        st.warning("No graph data available. Make sure Neo4j is connected.")


# ---------------------------------------------------------------------------
# Gate 1: Hypothesis Review Panel
# ---------------------------------------------------------------------------

if st.session_state.optimizer_gate == "gate1" and st.session_state.optimizer_selected_pattern:
    pattern = st.session_state.optimizer_selected_pattern

    with st.expander("🔬 Gate 1: Review Hypotheses", expanded=True):
        st.markdown(f"**Pattern:** {pattern.agent_name} / {pattern.criterion_id}")
        st.markdown(f"**Description:** {pattern.description}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Frequency", pattern.frequency)
        with col2:
            score_color = "green" if pattern.avg_score >= 0.7 else "orange" if pattern.avg_score >= 0.5 else "red"
            st.markdown(f"**Avg Score:** <span style='color:{score_color}'>{pattern.avg_score:.2f}</span>", unsafe_allow_html=True)

        # Sample queries
        if pattern.sample_queries:
            with st.expander("📝 Sample Failing Queries", expanded=False):
                for q in pattern.sample_queries[:5]:
                    st.write(f"- {q}")

        st.markdown("### Root Cause Hypotheses")
        st.caption("Edit or add hypotheses before generating variants")

        # Editable hypotheses
        edited_hypotheses = []
        for i, hyp in enumerate(st.session_state.optimizer_edited_hypotheses):
            edited = st.text_input(
                f"Hypothesis {i+1}",
                value=hyp,
                key=f"hyp_input_{i}"
            )
            if edited.strip():
                edited_hypotheses.append(edited.strip())

        # Add new hypothesis
        new_hyp = st.text_input("Add new hypothesis", key="new_hypothesis", placeholder="Enter a new hypothesis...")
        if new_hyp.strip():
            edited_hypotheses.append(new_hyp.strip())

        st.session_state.optimizer_edited_hypotheses = edited_hypotheses

        # Action buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve & Generate Variants", type="primary", key="gate1_approve"):
                if not edited_hypotheses:
                    st.error("Please provide at least one hypothesis")
                else:
                    with st.spinner("Generating variants..."):
                        try:
                            from src.optimizer import VariantGenerator, get_analyzer

                            # Update pattern with edited hypotheses
                            pattern.root_cause_hypotheses = edited_hypotheses
                            analyzer = get_analyzer()
                            analyzer.update_pattern_status(pattern.id, "reviewing")

                            # Generate variants
                            generator = VariantGenerator()
                            variants = generator.generate_variants(pattern, num_variants=3)
                            st.session_state.optimizer_variants = variants

                            # Run tests
                            with st.spinner("Running tests on variants..."):
                                from src.optimizer import TestRunner
                                runner = TestRunner()
                                results = runner.run_tests(pattern.agent_name, variants)
                                st.session_state.optimizer_test_results = results

                            st.session_state.optimizer_gate = "gate2"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to generate variants: {e}")

        with col2:
            if st.button("❌ Reject Pattern", key="gate1_reject"):
                try:
                    from src.optimizer import get_analyzer
                    analyzer = get_analyzer()
                    analyzer.update_pattern_status(pattern.id, "resolved")
                except Exception:
                    pass
                st.session_state.optimizer_gate = None
                st.session_state.optimizer_selected_pattern = None
                st.session_state.optimizer_edited_hypotheses = []
                st.rerun()


# ---------------------------------------------------------------------------
# Gate 2: Prompt Approval Panel
# ---------------------------------------------------------------------------

if st.session_state.optimizer_gate == "gate2" and st.session_state.optimizer_test_results:
    results = st.session_state.optimizer_test_results
    pattern = st.session_state.optimizer_selected_pattern

    with st.expander("🎯 Gate 2: Approve Prompt Change", expanded=True):
        st.markdown(f"**Agent:** {pattern.agent_name}")
        st.markdown("### Test Results (Ranked by Performance)")

        # Show all variants with results
        for i, result in enumerate(results):
            is_best = i == 0
            variant = result.variant

            with st.container():
                # Header
                if is_best:
                    st.markdown(f"#### 🏆 Variant {i+1} (Best)")
                else:
                    st.markdown(f"#### Variant {i+1}")

                # Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    delta_color = "green" if result.performance_delta > 0 else "red" if result.performance_delta < 0 else "gray"
                    st.markdown(f"**Delta:** <span style='color:{delta_color}'>{result.performance_delta:+.1%}</span>", unsafe_allow_html=True)
                with col2:
                    st.metric("Pass Rate", f"{result.pass_rate:.0%}")
                with col3:
                    st.write(f"Passed: {result.passed_count}/{result.passed_count + result.failed_count}")

                # Rationale
                st.markdown(f"**Rationale:** {variant.rationale}")

                # Diff view (collapsed)
                with st.expander("📋 View Prompt Diff", expanded=is_best):
                    try:
                        from src.optimizer import VariantGenerator, get_registry
                        generator = VariantGenerator()
                        registry = get_registry()

                        current_version = registry.get_current_version(variant.agent_name)
                        if current_version:
                            current_prompt = current_version.prompt_content
                        else:
                            current_prompt = generator._load_current_prompt(variant.agent_name)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Current Prompt**")
                            st.code(current_prompt[:1000] + "..." if len(current_prompt) > 1000 else current_prompt, language="text")
                        with col2:
                            st.markdown("**Proposed Prompt**")
                            st.code(variant.prompt_content[:1000] + "..." if len(variant.prompt_content) > 1000 else variant.prompt_content, language="text")
                    except Exception as e:
                        st.error(f"Could not load prompts: {e}")

                # Select button for non-best variants
                if not is_best:
                    if st.button(f"Select Variant {i+1}", key=f"select_var_{i}"):
                        # Move this variant to the front
                        st.session_state.optimizer_test_results = [result] + [r for r in results if r != result]
                        st.rerun()

                st.markdown("---")

        # Action buttons for best variant
        st.markdown("### Actions")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Approve & Activate", type="primary", key="gate2_approve"):
                best_result = results[0]
                with st.spinner("Activating new prompt..."):
                    try:
                        from src.optimizer import VariantGenerator, get_registry, get_analyzer

                        generator = VariantGenerator()
                        registry = get_registry()
                        analyzer = get_analyzer()

                        # Apply the variant (creates new version)
                        version_id = generator.apply_variant(
                            best_result.variant,
                            test_results=best_result.scores,
                            performance_delta=best_result.performance_delta,
                        )

                        # Activate the version
                        registry.activate_version(version_id, approved_by="streamlit_user")

                        # Mark pattern as resolved
                        analyzer.update_pattern_status(pattern.id, "resolved")

                        st.success(f"Activated new prompt version: {version_id}")

                        # Clear optimizer state
                        st.session_state.optimizer_gate = None
                        st.session_state.optimizer_selected_pattern = None
                        st.session_state.optimizer_variants = []
                        st.session_state.optimizer_test_results = []
                        st.session_state.optimizer_patterns = []

                        st.rerun()
                    except Exception as e:
                        st.error(f"Activation failed: {e}")

        with col2:
            if st.button("🔄 Re-run Tests", key="gate2_retest"):
                with st.spinner("Re-running tests..."):
                    try:
                        from src.optimizer import TestRunner
                        runner = TestRunner()
                        results = runner.run_tests(pattern.agent_name, st.session_state.optimizer_variants)
                        st.session_state.optimizer_test_results = results
                        st.rerun()
                    except Exception as e:
                        st.error(f"Re-test failed: {e}")

        with col3:
            if st.button("❌ Reject All", key="gate2_reject"):
                st.session_state.optimizer_gate = None
                st.session_state.optimizer_selected_pattern = None
                st.session_state.optimizer_variants = []
                st.session_state.optimizer_test_results = []
                st.rerun()


# ---------------------------------------------------------------------------
# Version History Panel
# ---------------------------------------------------------------------------

if st.session_state.optimizer_show_history:
    with st.expander("📜 Prompt Version History", expanded=True):
        agents = ["synthesizer", "intent_classifier", "search_planner", "graph_retriever"]
        selected_agent = st.selectbox("Select Agent", agents, key="history_agent")

        try:
            from src.optimizer import get_registry
            registry = get_registry()
            versions = registry.get_version_history(selected_agent, limit=10)
            current = registry.get_current_version(selected_agent)

            if versions:
                for v in versions:
                    is_active = v.is_active

                    with st.container():
                        # Version header
                        if is_active:
                            st.markdown(f"#### v{v.version} 🟢 ACTIVE")
                        else:
                            st.markdown(f"#### v{v.version}")

                        # Details
                        col1, col2 = st.columns(2)
                        with col1:
                            delta_color = "green" if v.performance_delta > 0 else "red" if v.performance_delta < 0 else "gray"
                            st.markdown(f"**Delta:** <span style='color:{delta_color}'>{v.performance_delta:+.1%}</span>", unsafe_allow_html=True)
                        with col2:
                            if v.approved_at:
                                st.write(f"Approved: {v.approved_at.strftime('%Y-%m-%d %H:%M')}")

                        st.markdown(f"**Rationale:** {v.rationale}")

                        # Rollback button (not for active version)
                        if not is_active:
                            if st.button(f"⏪ Rollback to v{v.version}", key=f"rollback_{v.id}"):
                                with st.spinner("Rolling back..."):
                                    try:
                                        success = registry.rollback(selected_agent, to_version=v.id)
                                        if success:
                                            st.success(f"Rolled back to v{v.version}")
                                            st.rerun()
                                        else:
                                            st.error("Rollback failed")
                                    except Exception as e:
                                        st.error(f"Rollback failed: {e}")

                        st.markdown("---")
            else:
                st.info(f"No version history for {selected_agent}")

        except Exception as e:
            st.error(f"Failed to load version history: {e}")

        # Close button
        if st.button("Close History", key="close_history"):
            st.session_state.optimizer_show_history = False
            st.rerun()
