"""
Streamlit Chat UI for Talk-to-Your-Database Agent.
"""
from __future__ import annotations

import json
from typing import Any

import plotly.graph_objects as go
import requests
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Talk to Your Database",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000"

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Dark background */
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }

/* Chat bubbles */
.user-bubble {
    background: linear-gradient(135deg, #1a3a5c 0%, #0d2137 100%);
    border: 1px solid #1f6feb;
    border-radius: 12px 12px 2px 12px;
    padding: 12px 16px;
    margin: 8px 0;
    color: #e6edf3;
}
.assistant-bubble {
    background: linear-gradient(135deg, #1c1f26 0%, #13151b 100%);
    border: 1px solid #30363d;
    border-radius: 12px 12px 12px 2px;
    padding: 12px 16px;
    margin: 8px 0;
    color: #e6edf3;
}
.sql-block {
    background: #0d1117;
    border: 1px solid #388bfd44;
    border-left: 3px solid #388bfd;
    border-radius: 6px;
    padding: 10px 14px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    color: #79c0ff;
    white-space: pre-wrap;
    margin: 8px 0;
}
.metric-pill {
    display: inline-block;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 12px;
    color: #8b949e;
    margin: 2px;
}
.success-badge {
    color: #3fb950;
    font-weight: bold;
}
.error-badge {
    color: #f85149;
    font-weight: bold;
}
h1, h2, h3 { color: #e6edf3 !important; }
.stButton button {
    background: linear-gradient(135deg, #1a3a5c, #0d2137);
    color: #79c0ff;
    border: 1px solid #1f6feb;
    border-radius: 8px;
}
.stButton button:hover { border-color: #388bfd; color: #ffffff; }
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role, content, payload}
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def call_ask(question: str) -> dict:
    payload = {
        "question": question,
        "conversation_history": st.session_state.conversation_history[-6:],
    }
    resp = requests.post(f"{API_BASE}/ask", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def call_feedback(question: str, sql: str, is_correct: bool) -> str:
    payload = {"question": question, "sql": sql, "is_correct": is_correct}
    resp = requests.post(f"{API_BASE}/ask/feedback", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get("message", "")


def call_train() -> dict:
    resp = requests.post(f"{API_BASE}/train/full", timeout=15)
    resp.raise_for_status()
    return resp.json()


def poll_train_status(placeholder) -> None:
    """Poll /train/status every 3s and update the placeholder."""
    import time
    for _ in range(120):  # max 6 minutes
        time.sleep(3)
        try:
            r = requests.get(f"{API_BASE}/train/status", timeout=10)
            s = r.json()
            state = s.get("state", "")
            msg = s.get("message", "")
            items = s.get("items_trained", 0)
            if state == "done":
                placeholder.success(f"✅ {msg}")
                return
            elif state == "error":
                placeholder.error(f"❌ {msg}")
                return
            else:
                placeholder.info(f"⏳ {msg} ({items} items so far…)")
        except Exception:
            pass
    placeholder.warning("Training is taking unusually long. Check the API logs.")


def render_result(payload: dict) -> None:
    """Render the assistant's answer: SQL, table, chart, feedback."""
    if payload.get("error"):
        st.markdown(
            f'<span class="error-badge">⚠️ Error:</span> {payload["error"]}',
            unsafe_allow_html=True,
        )
        return

    # SQL block
    st.markdown(
        f'<div class="sql-block">{payload["sql"]}</div>', unsafe_allow_html=True
    )

    # Metrics row
    rows = payload.get("rows", 0)
    retries = payload.get("retries", 0)
    st.markdown(
        f'<span class="metric-pill">📊 {rows} rows</span>'
        f'<span class="metric-pill">🔄 {retries} retries</span>',
        unsafe_allow_html=True,
    )

    # Data table
    if payload.get("data"):
        import pandas as pd

        df = pd.DataFrame(payload["data"])
        st.dataframe(df, use_container_width=True, height=300)

    # Plotly chart
    if payload.get("chart"):
        fig = go.Figure(payload["chart"])
        st.plotly_chart(fig, use_container_width=True)

    # Feedback buttons
    col_up, col_down, _ = st.columns([1, 1, 8])
    with col_up:
        if st.button("👍", key=f"up_{id(payload)}"):
            msg = call_feedback(payload["question"], payload["sql"], True)
            st.success(msg)
    with col_down:
        if st.button("👎", key=f"dn_{id(payload)}"):
            msg = call_feedback(payload["question"], payload["sql"], False)
            st.info(msg)


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗄️ DB Agent")
    st.markdown("---")

    st.markdown("### 🎓 Training")
    if st.button("Load Chinook Training Data", use_container_width=True):
        try:
            call_train()
            status_placeholder = st.empty()
            status_placeholder.info("⏳ Training started…")
            poll_train_status(status_placeholder)
        except Exception as exc:
            st.error(str(exc))

    st.markdown("---")
    st.markdown("### 💬 Conversation")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📖 Example Questions")
    examples = [
        "Who are the top 5 customers by total spending?",
        "List all albums by Led Zeppelin",
        "Show monthly revenue for 2013",
        "Which genre has the most tracks?",
        "What are the longest tracks?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=f"ex_{ex[:20]}"):
            st.session_state._prefill = ex

    st.markdown("---")
    st.caption("Powered by Vanna · Claude · ChromaDB")

# ──────────────────────────────────────────────────────────────────────────────
# Main chat area
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("# 🗄️ Talk to Your Database")
st.markdown(
    "Ask questions in plain English. The agent converts them to SQL, runs the query, and visualises the results."
)
st.markdown("---")

# Render chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">👤 {msg["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="assistant-bubble">', unsafe_allow_html=True)
        render_result(msg["payload"])
        st.markdown("</div>", unsafe_allow_html=True)

# Prefill from sidebar example click
prefill = st.session_state.pop("_prefill", "")

# Chat input
user_input = st.chat_input(
    placeholder="e.g. Who are the top 5 customers by revenue?",
)
if not user_input and prefill:
    user_input = prefill

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.conversation_history.append(
        {"role": "user", "content": user_input}
    )

    # Call backend
    with st.spinner("Generating SQL and querying the database…"):
        try:
            data = call_ask(user_input)
        except Exception as exc:
            data = {
                "question": user_input,
                "sql": "",
                "success": False,
                "retries": 0,
                "error": str(exc),
                "rows": 0,
                "columns": [],
                "data": [],
                "chart": None,
            }

    # Store assistant message
    st.session_state.messages.append(
        {"role": "assistant", "content": "", "payload": data}
    )
    # Update conversation history with a summary
    assistant_summary = (
        f"[Generated SQL: {data.get('sql', '')[:200]}]"
        if data.get("sql")
        else "[Failed to generate SQL]"
    )
    st.session_state.conversation_history.append(
        {"role": "assistant", "content": assistant_summary}
    )

    st.rerun()
