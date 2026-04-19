"""Session-level rate limiting for the agent."""

import os
import streamlit as st

DAILY_LIMIT = int(os.getenv("DAILY_AGENT_RUN_LIMIT", "5"))

def check_and_increment() -> tuple[bool, str]:
    current = st.session_state.get("agent_runs", 0)
    if current >= DAILY_LIMIT:
        return False, (
            f"You've reached the session limit of {DAILY_LIMIT} agent runs. "
            "This protects against runaway API costs. Refresh the page or come back tomorrow."
        )
    st.session_state.agent_runs = current + 1
    return True, f"Run {current + 1} of {DAILY_LIMIT} this session."

def get_runs_remaining() -> int:
    return max(0, DAILY_LIMIT - st.session_state.get("agent_runs", 0))
