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

def fetch_kg_subgraph(center_id: str = None, max_nodes: int = 50) -> tuple[list, list]:
    """Fetch a subgraph from Neo4j centered on an entity or overview."""
    nodes = []
    edges = []
    seen_nodes = set()

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
                results = client.run_cypher(query, {"center_id": center_id})
            else:
                # Fetch overview: Principles -> Methods -> Implementations
                query = """
                MATCH (p:Principle)<-[a:ADDRESSES]-(m:Method)
                OPTIONAL MATCH (m)<-[i:IMPLEMENTS]-(impl:Implementation)
                RETURN p, a, m, i, impl
                LIMIT 200
                """
                results = client.run_cypher(query)

            for record in results:
                for key, value in record.items():
                    if value is None:
                        continue

                    # Handle nodes
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

                    # Handle relationships
                    elif isinstance(value, dict) and "type" in value:
                        rel_type = value.get("type", "")
                        start = value.get("start_node", {}).get("properties", {}).get("id")
                        end = value.get("end_node", {}).get("properties", {}).get("id")
                        if start and end:
                            edges.append(Edge(
                                source=start,
                                target=end,
                                label=rel_type[:10],
                                color="#888888"
                            ))

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

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.last_web_results = []
        st.session_state.pending_proposal = None
        st.session_state.graph_data = None
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
                    result = run_agent(prompt)
                finally:
                    settings.llm_provider = original_provider
                    settings.llm_model = original_model

                answer = result.get("answer") or "I couldn't find relevant information."
                sources = result.get("sources") or []
                intent = result.get("intent")
                confidence = result.get("confidence")
                web_results = result.get("web_results") or []

                # Store web results for "Add to KG" feature
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

    if graph_mode == "From Last Query" and st.session_state.messages:
        # Try to get the last result from state (would need to store raw results)
        # For now, show a message that query results aren't stored for graph
        st.info("Query result visualization requires raw KG results. Use 'Overview' mode for now.")
        nodes, edges = fetch_kg_subgraph(max_nodes=max_nodes)
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
