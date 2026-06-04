from __future__ import annotations

from typing import Optional

from agent.tools.birth_chart import compute_birth_chart
from agent.tools.geocode import geocode_place


def precompute_chart(birth_details: Optional[dict]) -> Optional[dict]:
    """Geocode + compute a birth chart deterministically, in plain Python.

    When the user submits the birth form we already have date, time, and place,
    so there's no reason to spend two LLM tool-calling rounds (geocode → compute)
    rediscovering them. Doing it in code here means the chart is in state before
    the agent runs — the model goes straight to interpreting, which on the free
    Gemini tier is the difference between ~5 requests per message and ~1.

    Returns the chart dict on success, or None if details are incomplete or the
    place is ambiguous — in which case we fall back to the agent resolving it
    conversationally (e.g. asking the user for a more specific city).
    """
    if not birth_details:
        return None

    date = (birth_details.get("date") or "").strip()
    place = (birth_details.get("place") or "").strip()
    time = (birth_details.get("time") or "").strip() or "12:00"
    if not date or not place:
        return None

    geo = geocode_place.invoke({"place_name": place})
    if not isinstance(geo, dict) or "lat" not in geo:
        # ambiguous country, lookup error, or unknown place — let the agent ask.
        return None

    chart = compute_birth_chart.invoke({
        "date": date,
        "time": time,
        "lat": geo["lat"],
        "lng": geo["lng"],
        "timezone": geo["timezone"],
    })
    if not isinstance(chart, dict) or "planets" not in chart:
        return None

    return chart
