from __future__ import annotations

import json

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.nodes import (
    reasoning_node,
    router_node,
    safety_node,
    should_use_tools,
)
from agent.state import AgentState
from agent.tools import TOOLS


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
    builder.add_node("reasoning", reasoning_node)
    builder.add_node("tools", tool_node)
    builder.add_node("cache_chart", cache_birth_chart)
    builder.add_node("safety", safety_node)

    builder.set_entry_point("router")

    builder.add_conditional_edges(
        "router",
        lambda s: s["intent"],
        {
            "chart_request": "reasoning",
            "daily_horoscope": "reasoning",
            "freeform": "reasoning",
            "off_topic": "safety",
        },
    )

    builder.add_conditional_edges(
        "reasoning",
        should_use_tools,
        {"tools": "tools", "safety": "safety"},
    )

    # after tools, cache any chart result then loop back to reasoning
    builder.add_edge("tools", "cache_chart")
    builder.add_edge("cache_chart", "reasoning")
    builder.add_edge("safety", END)

    return builder.compile()


graph = build_graph()
