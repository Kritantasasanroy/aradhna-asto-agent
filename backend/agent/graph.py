from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.nodes import (
    reasoning_node,
    router_node,
    safety_node,
    should_use_tools,
    tool_node,
)
from agent.state import AgentState


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("router", router_node)
    builder.add_node("reasoning", reasoning_node)
    builder.add_node("tools", tool_node)
    builder.add_node("safety", safety_node)

    builder.set_entry_point("router")

    # off_topic messages skip straight to safety which will redirect warmly
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

    # after reasoning, either loop through tools or wrap up
    builder.add_conditional_edges(
        "reasoning",
        should_use_tools,
        {"tools": "tools", "safety": "safety"},
    )

    builder.add_edge("tools", "reasoning")
    builder.add_edge("safety", END)

    return builder.compile()


graph = build_graph()
