"""Temporary test page for Phase 1 — verifies the agent loop works."""

import streamlit as st
from utils.agent_orchestrator import run_agent
from utils.rate_limit import check_and_increment, get_runs_remaining

st.title("🧪 Agent Test Page (Phase 1)")
st.info(f"Runs remaining this session: {get_runs_remaining()}")

user_goal = st.text_input(
    "Give the agent a goal",
    value="Use the ping tool with the message 'hello world' and tell me what it returned.",
)

if st.button("🚀 Run Agent"):
    allowed, msg = check_and_increment()
    if not allowed:
        st.error(msg)
        st.stop()

    st.caption(msg)

    with st.status("Agent thinking...", expanded=True) as status:
        for event in run_agent(user_goal):
            if event["type"] == "thinking":
                st.markdown(f"💭 **Thinking:** {event['content']}")
            elif event["type"] == "tool_call":
                st.markdown(f"🔧 **Calling tool:** `{event['tool_name']}({event['tool_input']})`")
            elif event["type"] == "tool_result":
                st.markdown(f"✅ **Tool returned:** `{event['result']}`")
            elif event["type"] == "final":
                st.markdown(f"🎯 **Final answer:** {event['content']}")
                status.update(label="Done", state="complete")
            elif event["type"] == "error":
                st.error(event["content"])
                status.update(label="Error", state="error")
