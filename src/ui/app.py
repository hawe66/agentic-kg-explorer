"""Streamlit UI for Agentic KG Explorer."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st

from config.settings import get_settings
from src.agents.graph import run_agent
from src.api.kg_writer import propose_node, approve_node, WebResult, ProposedNode


st.set_page_config(
    page_title="Agentic KG Explorer",
    page_icon="🔍",
    layout="wide",
)

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
        "How does LangGraph work?",
        "What are the latest AI agent frameworks?",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.last_web_results = []
        st.session_state.pending_proposal = None
        st.rerun()


# ---------------------------------------------------------------------------
# Add to KG Modal (if pending proposal exists)
# ---------------------------------------------------------------------------

if st.session_state.pending_proposal is not None:
    proposal = st.session_state.pending_proposal

    if proposal.exists_in_kg:
        st.warning("⚠️ This entity already exists in KG. Review and click 'Update Node' to modify.")
        st.subheader("📝 Update Knowledge Graph Node")
    else:
        st.warning("⬇️ Review the proposed node below and click 'Create Node' to add to KG")
        st.subheader("📝 Add to Knowledge Graph")

    with st.form("approve_node_form"):
        if proposal.exists_in_kg:
            st.write(f"**Update existing {proposal.node_type}**")
        else:
            st.write(f"**Proposed {proposal.node_type}**")

        # Editable fields
        node_id = st.text_input("Node ID", value=proposal.node_id, disabled=proposal.exists_in_kg)
        name = st.text_input("Name", value=proposal.name)

        # Show existing description for comparison if updating
        if proposal.exists_in_kg and proposal.existing_description:
            st.caption("Current description in KG:")
            st.text(proposal.existing_description[:200] + "..." if len(proposal.existing_description or "") > 200 else proposal.existing_description)

        description = st.text_area("Description (new)", value=proposal.description)

        col1, col2 = st.columns(2)

        if proposal.node_type == "Method":
            with col1:
                method_family = st.selectbox(
                    "Method Family",
                    ["prompting_decoding", "agent_loop_pattern", "workflow_orchestration",
                     "retrieval_grounding", "memory_system", "reflection_verification",
                     "multi_agent_coordination", "training_alignment", "safety_control",
                     "evaluation", "observability_tracing"],
                    index=0 if not proposal.method_family else None,
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

        st.caption(f"Source: {proposal.source_url}")
        st.caption(f"Confidence: {proposal.confidence:.0%}")

        col1, col2 = st.columns(2)
        with col1:
            button_label = "✅ Update Node" if proposal.exists_in_kg else "✅ Create Node"
            submitted = st.form_submit_button(button_label, type="primary")
        with col2:
            cancelled = st.form_submit_button("❌ Cancel")

        if submitted:
            # Build updated proposal
            updated = ProposedNode(
                node_type=proposal.node_type,
                node_id=node_id,
                name=name,
                description=description,
                method_family=method_family if proposal.node_type == "Method" else None,
                method_type=proposal.method_type,
                granularity=granularity if proposal.node_type == "Method" else None,
                addresses=proposal.addresses,
                impl_type=impl_type if proposal.node_type == "Implementation" else None,
                maintainer=maintainer if proposal.node_type == "Implementation" else None,
                source_repo=proposal.source_repo,
                implements=proposal.implements,
                doc_type=doc_type if proposal.node_type == "Document" else None,
                authors=proposal.authors,
                year=year if proposal.node_type == "Document" else None,
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

    st.divider()


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


# Chat input
if prompt := st.chat_input("Ask about agentic AI methods, implementations, or principles..."):
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
# Web Results with "Add to KG" buttons
# ---------------------------------------------------------------------------

# Debug: show web results count
if st.session_state.last_web_results:
    st.info(f"💡 {len(st.session_state.last_web_results)} web results available. Click 'Add to KG' to import to knowledge graph.")

if st.session_state.last_web_results:
    st.subheader("🌐 Web Search Results")
    st.caption("Click 'Add to KG' to propose adding this content to the knowledge graph")

    for i, wr in enumerate(st.session_state.last_web_results):
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"**[{wr.get('title', 'Untitled')}]({wr.get('url', '')})**")
                st.write(wr.get("content", "")[:300] + "...")

            with col2:
                if st.button("➕ Add to KG", key=f"add_kg_{i}"):
                    with st.spinner("Extracting entity..."):
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
                            st.error("Could not extract entity from this content")

            st.divider()
