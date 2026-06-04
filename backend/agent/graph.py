from __future__ import annotations

import json

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.nodes import (
    after_gate,
    editor_node,
    reasoning_node,
    router_node,
    safety_node,
    sensitivity_gate_node,
    should_use_tools,
)
from agent.state import AgentState
from agent.tools import TOOLS

try:
    from langgraph.checkpoint.memory import MemorySaver
    _checkpointer = MemorySaver()
except ImportError:
    _checkpointer = None


def cache_birth_chart(state: AgentState) -> dict:
    """
    After tools run, check if compute_birth_chart produced a result and cache
    it in state so we don't recompute it on every turn.
    """
    if state.get("birth_chart"):
        return {}  # already cached

    for msg in reversed(state["messages"]):
        if getattr(msg, "name", None) == "compute_birth_chart":
            try:
                result = json.loads(msg.content)
                if "planets" in result:
                    return {"birth_chart": result}
            except (json.JSONDecodeError, TypeError):
                pass
    return {}


def build_graph() -> StateGraph:
    tool_node = ToolNode(TOOLS)

    builder = StateGraph(AgentState)

    builder.add_node("router", router_node)
    builder.add_node("sensitivity_gate", sensitivity_gate_node)
    builder.add_node("reasoning", reasoning_node)
    builder.add_node("tools", tool_node)
    builder.add_node("cache_chart", cache_birth_chart)
    builder.add_node("safety", safety_node)
    builder.add_node("editor", editor_node)

    builder.set_entry_point("router")

    # off_topic skips the sensitivity gate and reasoning entirely
    builder.add_conditional_edges(
        "router",
        lambda s: s["intent"],
        {
            "chart_request": "sensitivity_gate",
            "daily_horoscope": "sensitivity_gate",
            "freeform": "sensitivity_gate",
            "off_topic": "safety",
        },
    )

    # If the gate produced a cancellation message, skip reasoning and go to safety.
    # Otherwise proceed to reasoning normally.
    builder.add_conditional_edges(
        "sensitivity_gate",
        after_gate,
        {"reasoning": "reasoning", "safety": "safety"},
    )

    builder.add_conditional_edges(
        "reasoning",
        should_use_tools,
        {"tools": "tools", "safety": "safety"},
    )

    # after tools, cache any chart result then loop back to reasoning
    builder.add_edge("tools", "cache_chart")
    builder.add_edge("cache_chart", "reasoning")

    # safety hands off to the editor (second agent), which softens tone on long
    # readings and passes everything else through untouched
    builder.add_edge("safety", "editor")
    builder.add_edge("editor", END)

    return builder.compile(checkpointer=_checkpointer)


graph = build_graph()
