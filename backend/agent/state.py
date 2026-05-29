from __future__ import annotations

from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BirthDetails(TypedDict, total=False):
    date: str   # YYYY-MM-DD
    time: str   # HH:MM in 24-hour format
    place: str  # city name or "City, Country"


class AgentState(TypedDict):
    # add_messages handles appending new messages rather than overwriting
    messages: Annotated[list[BaseMessage], add_messages]

    # birth details from the user — might be partial (no time, etc.)
    birth_details: Optional[BirthDetails]

    # cached after the first chart computation so we don't recompute every turn
    birth_chart: Optional[dict]

    # router fills this in: chart_request | daily_horoscope | freeform | off_topic
    intent: str

    # tracks which tools fired this turn — useful for eval assertions
    tool_calls_made: list[str]

    # hard stop at 8 steps to prevent runaway loops
    step_count: int

    session_id: str
