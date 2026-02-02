"""Streamlit Chat UI for Agentic KG Explorer."""

import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Agentic KG Explorer", page_icon=":mag:", layout="wide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_metadata(meta: dict):
    """Render expandable detail sections for an assistant response."""
    confidence = meta.get("confidence")
    if confidence is not None:
        pct = int(confidence * 100)
        color = "green" if pct >= 70 else ("orange" if pct >= 40 else "red")
        st.markdown(f"**Confidence:** :{color}[{pct}%]")

    intent = meta.get("intent")
    entities = meta.get("entities", [])
    if intent or entities:
        with st.expander("Intent & Entities"):
            if intent:
                st.markdown(f"**Intent:** `{intent}`")
            if entities:
                st.markdown("**Entities:** " + ", ".join(f"`{e}`" for e in entities))

    sources = meta.get("sources", [])
    if sources:
        with st.expander("Sources"):
            for s in sources:
                st.markdown(f"- **{s.get('type')}** `{s.get('id')}` — {s.get('name')}")

    vector_results = meta.get("vector_results", [])
    if vector_results:
        with st.expander("Vector Results"):
            st.dataframe(
                [
                    {
                        "node_id": v.get("node_id"),
                        "label": v.get("node_label"),
                        "score": round(v.get("score", 0), 4),
                    }
                    for v in vector_results
                ],
                use_container_width=True,
            )

    cypher = meta.get("cypher_executed", [])
    if cypher:
        with st.expander("Cypher Queries"):
            for q in cypher:
                st.code(q, language="cypher")

    kg_results = meta.get("kg_results", [])
    if kg_results:
        with st.expander("Raw KG Results"):
            st.json(kg_results)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Settings")
    api_url = st.text_input("API URL", value="http://localhost:8000")

    st.subheader("LLM Override")
    provider = st.selectbox(
        "Provider",
        options=["(default)", "openai", "anthropic", "gemini"],
        index=0,
    )
    model_options = {
        "(default)": ["(default)"],
        "openai": ["(default)", "gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini"],
        "anthropic": ["(default)", "claude-3-5-sonnet-20241022", "claude-sonnet-4-20250514"],
        "gemini": ["(default)", "gemini-2.5-flash", "gemini-2.0-flash"],
    }
    model = st.selectbox("Model", options=model_options.get(provider, ["(default)"]), index=0)

    st.divider()
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("Agentic KG Explorer")

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("metadata"):
            _render_metadata(msg["metadata"])

# Handle new input
if prompt := st.chat_input("Ask about the knowledge graph..."):
    # Show and store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API and show assistant response
    with st.chat_message("assistant"):
        meta = {}
        answer = ""
        with st.spinner("Querying agent pipeline..."):
            try:
                payload = {"query": prompt}
                if provider != "(default)":
                    payload["llm_provider"] = provider
                if model != "(default)":
                    payload["llm_model"] = model

                resp = httpx.post(
                    f"{api_url.rstrip('/')}/query",
                    json=payload,
                    timeout=120.0,
                )
                resp.raise_for_status()
                data = resp.json()

                answer = data.get("answer") or data.get("error") or "No answer returned."
                meta = {
                    "intent": data.get("intent"),
                    "entities": data.get("entities", []),
                    "confidence": data.get("confidence"),
                    "sources": data.get("sources", []),
                    "vector_results": data.get("vector_results", []),
                    "cypher_executed": data.get("cypher_executed", []),
                    "kg_results": data.get("kg_results", []),
                }

                if data.get("error"):
                    st.error(data["error"])
                else:
                    st.markdown(answer)

            except httpx.ConnectError:
                answer = "Could not connect to the API server. Is FastAPI running?"
                st.error(answer)
            except httpx.HTTPStatusError as e:
                answer = f"API error: {e.response.status_code} — {e.response.text}"
                st.error(answer)
            except Exception as e:
                answer = f"Unexpected error: {e}"
                st.error(answer)

        _render_metadata(meta)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "metadata": meta}
    )
