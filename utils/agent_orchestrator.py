"""
Agent orchestrator using Anthropic Claude API with tool use.
Implements the agent loop, streaming, and 3-layer cost protection.
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────
# Phase 1: use Haiku for testing (cheaper). Switch to Sonnet in Phase 4.
AGENT_MODEL = "claude-haiku-4-5"
MAX_AGENT_ITERATIONS = 15
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# ── Tool registry ────────────────────────────────────────────────────────
TOOL_REGISTRY = {}

def register_tool(name, description, input_schema, handler):
    TOOL_REGISTRY[name] = {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "handler": handler,
    }

def get_tool_schemas():
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in TOOL_REGISTRY.values()
    ]

# ── Mock tool for Phase 1 verification ───────────────────────────────────

def _ping_handler(message: str) -> dict:
    return {"echo": f"pong: {message}", "status": "ok"}

register_tool(
    name="ping",
    description="A test tool that echoes a message back. Use this to verify the agent loop works.",
    input_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to echo"}
        },
        "required": ["message"],
    },
    handler=_ping_handler,
)

# ── The agent loop ───────────────────────────────────────────────────────

def run_agent(user_goal: str, on_event=None):
    if DEMO_MODE:
        yield {"type": "thinking", "content": "[DEMO MODE] Using cached response"}
        yield {"type": "final", "content": f"This is a demo response for: {user_goal}"}
        return

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": user_goal}]

    for iteration in range(MAX_AGENT_ITERATIONS):
        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=4096,
            tools=get_tool_schemas(),
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text
            yield {"type": "final", "content": final_text}
            return

        assistant_blocks = []
        tool_results = []

        for block in response.content:
            if block.type == "text":
                yield {"type": "thinking", "content": block.text}
                assistant_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                yield {
                    "type": "tool_call",
                    "tool_name": block.name,
                    "tool_input": block.input,
                    "tool_use_id": block.id,
                }
                assistant_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

                if block.name in TOOL_REGISTRY:
                    try:
                        result = TOOL_REGISTRY[block.name]["handler"](**block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                        yield {
                            "type": "tool_result",
                            "tool_name": block.name,
                            "result": result,
                        }
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True,
                        })
                        yield {"type": "error", "content": f"Tool {block.name} failed: {e}"}
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": f"Unknown tool: {block.name}"}),
                        "is_error": True,
                    })

        messages.append({"role": "assistant", "content": assistant_blocks})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    yield {"type": "error", "content": f"Max iterations ({MAX_AGENT_ITERATIONS}) reached"}
