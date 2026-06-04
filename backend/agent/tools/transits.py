from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

EPHE_PATH = str(Path(__file__).parent.parent.parent / "ephe")

PLANETS = {
    "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4,
    "Jupiter": 5, "Saturn": 6, "Uranus": 7, "Neptune": 8, "Pluto": 9,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

# how many degrees either side we consider the aspect active
ORB = 3.0


def _current_positions(date: str) -> dict:
    import swisseph as swe

    swe.set_ephe_path(EPHE_PATH)
    year, month, day = (int(p) for p in date.split("-"))
    # use noon UTC for a day-level reading
    jd = swe.julday(year, month, day, 12.0)

    positions = {}
    for name, pid in PLANETS.items():
        pos, _ = swe.calc_ut(jd, pid)
        sign = SIGNS[int(pos[0] / 30) % 12]
        positions[name] = {
            "longitude": round(pos[0], 4),
            "sign": sign,
            "retrograde": pos[3] < 0,
        }
    return positions


@tool
def get_daily_transits(date: str, natal_chart: dict = None) -> dict:
    """
    Get current planetary positions and how they aspect the natal chart.

    Finds active conjunctions, sextiles, squares, trines, and oppositions
    between today's sky and the user's natal planets. Returns the tightest
    transits sorted by orb so the most significant ones come first.

    date: YYYY-MM-DD — usually today's date
    natal_chart: the full output from compute_birth_chart. If omitted or
                 incomplete, the current sky positions are returned without
                 aspect analysis — still useful for retrograde and sign questions.
    """
    try:
        import swisseph as swe  # noqa: F401
    except ImportError:
        return {"error": "pyswisseph is not installed. Run: pip install pyswisseph"}

    try:
        current = _current_positions(date)
    except Exception as e:
        return {"error": f"Could not compute current positions: {e}"}

    natal_planets = (natal_chart or {}).get("planets", {})

    active_transits = []
    for t_planet, t_data in current.items():
        for n_planet, n_data in natal_planets.items():
            diff = abs(t_data["longitude"] - n_data["longitude"])
            if diff > 180:
                diff = 360 - diff

            for aspect_name, angle in ASPECTS.items():
                orb = abs(diff - angle)
                if orb <= ORB:
                    active_transits.append({
                        "transit_planet": t_planet,
                        "aspect": aspect_name,
                        "natal_planet": n_planet,
                        "transit_sign": t_data["sign"],
                        "natal_sign": n_data["sign"],
                        "retrograde": t_data["retrograde"],
                        "orb": round(orb, 2),
                    })

    active_transits.sort(key=lambda t: t["orb"])

    return {
        "date": date,
        "current_sky": current,
        "active_transits": active_transits[:10],
        "note": "Transits sorted by orb (tightest first). Conjunctions and oppositions tend to be the most felt.",
    }
