from __future__ import annotations

import re
from datetime import date
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage

from agent.llm import get_llm
from agent.prompts import build_system_prompt
from agent.state import AgentState
from agent.tools.birth_chart import compute_birth_chart
from agent.tools.geocode import geocode_place
from agent.tools.knowledge import knowledge_lookup
from agent.tools.transits import get_daily_transits

TOOLS = [geocode_place, compute_birth_chart, get_daily_transits, knowledge_lookup]

STEP_LIMIT = 8

# phrases that indicate the model made a definitive claim it shouldn't
_SAFETY_PATTERNS = [
    r"you will (get|develop|have) (cancer|diabetes|a disease|an illness|a tumor)",
    r"you (have|will have) (cancer|a terminal|a fatal)",
    r"you will die (on|at|in|from|of)",
    r"(your death|death will occur|time of death)",
    r"(guaranteed (return|profit|income)|you should (buy|sell|invest) (on|at) \w+ \d)",
]

_DISCLAIMER = (
    "\n\n*A note: astrology offers reflection and possibility, not certainty. "
    "For medical, legal, or financial decisions, please consult the right professionals.*"
)


def router_node(state: AgentState) -> dict:
    """Classifies what the user is asking for."""
    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"), None
    )
    text = last_human.content.lower() if last_human else ""

    if any(w in text for w in ["chart", "birth", "natal", "rising", "ascendant", "house", "sign", "placement"]):
        intent = "chart_request"
    elif any(w in text for w in ["today", "horoscope", "transit", "energy", "retrograde", "this week", "right now"]):
        intent = "daily_horoscope"
    elif any(w in text for w in ["recipe", "weather", "sports", "news", "movie", "code", "program"]):
        intent = "off_topic"
    else:
        intent = "freeform"

    return {"intent": intent}


def reasoning_node(state: AgentState) -> dict:
    """Calls the LLM with tools bound. The main thinking step."""
    today = date.today().isoformat()
    system_content = build_system_prompt(
        today=today,
        birth_details=state.get("birth_details"),
        birth_chart=state.get("birth_chart"),
    )

    llm = get_llm(temperature=0.7).bind_tools(TOOLS)
    messages = [SystemMessage(content=system_content)] + list(state["messages"])
    response = llm.invoke(messages)

    tool_names = [tc["name"] for tc in (getattr(response, "tool_calls", None) or [])]

    return {
        "messages": [response],
        "step_count": state["step_count"] + 1,
        "tool_calls_made": list(state.get("tool_calls_made", [])) + tool_names,
    }


def safety_node(state: AgentState) -> dict:
    """
    Final check before the response goes out.

    Handles off-topic redirects and strips any language that makes
    definitive medical, legal, or financial claims.
    """
    # off-topic: respond with a warm redirect instead of running the LLM
    if state.get("intent") == "off_topic":
        reply = AIMessage(
            content=(
                "That's a bit outside my world — I'm here as your astrology companion. "
                "If you'd like to explore your birth chart, what the transits are doing, "
                "or what the planets might be saying about any part of your life, I'm all yours."
            )
        )
        return {"messages": [reply]}

    # check the last AI message for safety violations
    last = state["messages"][-1] if state["messages"] else None
    if last is None or getattr(last, "type", None) != "ai":
        return {}

    content = last.content
    if not isinstance(content, str):
        return {}

    flagged = any(re.search(p, content, re.IGNORECASE) for p in _SAFETY_PATTERNS)
    if flagged and _DISCLAIMER not in content:
        return {"messages": [AIMessage(content=content + _DISCLAIMER)]}

    return {}


def should_use_tools(state: AgentState) -> Literal["tools", "safety"]:
    """Routes back through tools if the LLM requested them, otherwise wraps up."""
    last = state["messages"][-1] if state["messages"] else None
    has_tool_calls = bool(getattr(last, "tool_calls", None))
    over_limit = state["step_count"] >= STEP_LIMIT

    if has_tool_calls and not over_limit:
        return "tools"
    return "safety"
