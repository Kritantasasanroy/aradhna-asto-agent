from __future__ import annotations

import re
import time
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

_RATE_LIMIT_FALLBACK = (
    "I'm sorry — the stars are a little crowded right now and I couldn't finish "
    "that reading. This is usually a brief rate limit on the free model. Please "
    "give it a few seconds and ask me again."
)


def router_node(state: AgentState) -> dict:
    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"), None
    )
    text = last_human.content.lower() if last_human else ""

    # off-topic is checked first — "what's the weather today?" contains "today"
    # but should not be classified as a horoscope request
    if any(w in text for w in ["recipe", "weather", "sports", "news", "movie", "code", "program"]):
        intent = "off_topic"
    elif any(w in text for w in ["chart", "birth", "natal", "rising", "ascendant", "house", "sign", "placement"]):
        intent = "chart_request"
    elif any(w in text for w in ["today", "horoscope", "transit", "energy", "retrograde", "this week", "right now"]):
        intent = "daily_horoscope"
    else:
        intent = "freeform"

    return {"intent": intent}


def _invoke_with_backoff(llm, messages, attempts: int = 4):
    """Retry on rate-limit 429s with exponential backoff: 4s, 8s, 16s."""
    last_err = None
    for i in range(attempts):
        try:
            return llm.invoke(messages)
        except Exception as e:
            last_err = e
            is_rate_limit = "429" in str(e) or "rate-limit" in str(e).lower()
            if not is_rate_limit or i == attempts - 1:
                raise
            time.sleep(4 * (2 ** i))
    raise last_err  # pragma: no cover


def reasoning_node(state: AgentState) -> dict:
    today = date.today().isoformat()
    system_content = build_system_prompt(
        today=today,
        birth_details=state.get("birth_details"),
        birth_chart=state.get("birth_chart"),
    )

    llm = get_llm(temperature=0.7).bind_tools(TOOLS)
    messages = [SystemMessage(content=system_content)] + list(state["messages"])

    try:
        response = _invoke_with_backoff(llm, messages)
    except Exception:
        fallback = AIMessage(content=_RATE_LIMIT_FALLBACK)
        fallback.additional_kwargs["degraded"] = True
        return {
            "messages": [fallback],
            "step_count": state["step_count"] + 1,
        }

    tool_names = [tc["name"] for tc in (getattr(response, "tool_calls", None) or [])]

    return {
        "messages": [response],
        "step_count": state["step_count"] + 1,
        "tool_calls_made": list(state.get("tool_calls_made", [])) + tool_names,
    }


def safety_node(state: AgentState) -> dict:
    if state.get("intent") == "off_topic":
        reply = AIMessage(
            content=(
                "That's a bit outside my world — I'm here as your astrology companion. "
                "If you'd like to explore your birth chart, what the transits are doing, "
                "or what the planets might be saying about any part of your life, I'm all yours."
            )
        )
        return {"messages": [reply]}

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
    last = state["messages"][-1] if state["messages"] else None
    has_tool_calls = bool(getattr(last, "tool_calls", None))
    over_limit = state["step_count"] >= STEP_LIMIT

    if has_tool_calls and not over_limit:
        return "tools"
    return "safety"
