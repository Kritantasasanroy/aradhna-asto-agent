from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage

from agent.state import AgentState

STEP_LIMIT = 8


def router_node(state: AgentState) -> dict:
    """Figures out what the user actually wants."""
    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"), None
    )
    text = last_human.content.lower() if last_human else ""

    if any(w in text for w in ["chart", "birth", "natal", "rising", "ascendant", "house", "sign"]):
        intent = "chart_request"
    elif any(w in text for w in ["today", "horoscope", "transit", "energy", "week", "retrograde"]):
        intent = "daily_horoscope"
    elif any(w in text for w in ["recipe", "weather", "sport", "stock", "news"]):
        intent = "off_topic"
    else:
        intent = "freeform"

    return {"intent": intent}


def reasoning_node(state: AgentState) -> dict:
    """Main reasoning step. Placeholder — gets replaced with real LLM call on Day 3."""
    reply = AIMessage(content="I'm here with you. Let me look into this for you...")
    return {
        "messages": [reply],
        "step_count": state["step_count"] + 1,
    }


def tool_node(state: AgentState) -> dict:
    """Executes tool calls requested by the reasoning node. Wired up on Day 3."""
    return {}


def safety_node(state: AgentState) -> dict:
    """
    Last stop before the response goes out. Strips any language that presents
    a reading as medical, legal, or financial certainty. Also softens anything
    that sounds like a definitive prediction.
    """
    # Real implementation on Day 3 — for now the state passes through unchanged
    return {}


def should_use_tools(state: AgentState) -> Literal["tools", "safety"]:
    """Decides whether to loop back through tools or wrap up."""
    last = state["messages"][-1] if state["messages"] else None
    has_tool_calls = hasattr(last, "tool_calls") and bool(last.tool_calls)
    over_limit = state["step_count"] >= STEP_LIMIT

    if has_tool_calls and not over_limit:
        return "tools"
    return "safety"
