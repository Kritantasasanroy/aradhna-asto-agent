from __future__ import annotations

from datetime import date as date_cls, datetime
from pathlib import Path

import pytz
from langchain_core.tools import tool

# pyswisseph falls back to the built-in Moshier ephemeris when data files
# aren't present — accurate enough for 1800–2400. For maximum precision,
# download files from astro.com/swisseph and place them in backend/ephe/.
EPHE_PATH = str(Path(__file__).parent.parent.parent / "ephe")

PLANETS = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _longitude_to_sign(longitude: float) -> tuple[str, float]:
    sign = SIGNS[int(longitude / 30) % 12]
    degree = round(longitude % 30, 2)
    return sign, degree


def _validate_birth_details(date: str, time: str) -> str | None:
    """Returns an error string for malformed or impossible dates/times, or None."""
    try:
        year, month, day = (int(p) for p in date.split("-"))
    except ValueError:
        return f"Date must be in YYYY-MM-DD format, got '{date}'."
    try:
        datetime(year, month, day)
    except ValueError:
        return f"'{date}' is not a real calendar date. Please double-check the day and month."

    try:
        hour, minute = (int(p) for p in time.split(":"))
    except ValueError:
        return f"Time must be in HH:MM 24-hour format, got '{time}'."
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return f"'{time}' is not a valid time of day. Use HH:MM between 00:00 and 23:59."

    return None


def _to_julian_day(date: str, time: str, timezone: str) -> float:
    import swisseph as swe

    hour, minute = (int(p) for p in time.split(":"))
    year, month, day = (int(p) for p in date.split("-"))
    local_tz = pytz.timezone(timezone)
    local_dt = local_tz.localize(datetime(year, month, day, hour, minute))
    utc = local_dt.astimezone(pytz.UTC)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60.0)


@tool
def compute_birth_chart(
    date: str,
    time: str,
    lat: float,
    lng: float,
    timezone: str,
) -> dict:
    """
    Compute a natal birth chart using real Swiss Ephemeris data.

    Returns planetary positions (sign, degree, retrograde flag) and house cusps.
    Call geocode_place first to get lat, lng, and timezone from a place name.

    date: YYYY-MM-DD
    time: HH:MM in 24-hour format. Use '12:00' when birth time is unknown.
    lat, lng: decimal degrees from geocode_place
    timezone: IANA timezone string e.g. 'Asia/Kolkata'
    """
    try:
        import swisseph as swe
    except ImportError:
        return {"error": "pyswisseph is not installed. Run: pip install pyswisseph"}

    validation_error = _validate_birth_details(date, time)
    if validation_error:
        return {"error": validation_error}

    try:
        swe.set_ephe_path(EPHE_PATH)
        jd = _to_julian_day(date, time, timezone)
    except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
        return {"error": f"Invalid date, time, or timezone: {e}"}
    except Exception as e:
        return {"error": f"Could not parse birth details: {e}"}

    try:
        planets: dict[str, dict] = {}
        for name, planet_id in PLANETS.items():
            pos, _ = swe.calc_ut(jd, planet_id)
            sign, degree = _longitude_to_sign(pos[0])
            planets[name] = {
                "longitude": round(pos[0], 4),
                "sign": sign,
                "degree": degree,
                "retrograde": pos[3] < 0,
            }

        # Placidus houses — most common system in Western astrology
        cusps, ascmc = swe.houses(jd, lat, lng, b"P")

        houses: dict[str, dict] = {}
        for i in range(12):
            sign, degree = _longitude_to_sign(cusps[i])
            houses[f"house_{i + 1}"] = {
                "sign": sign,
                "degree": degree,
                "longitude": round(cusps[i], 4),
            }

        asc_sign, asc_deg = _longitude_to_sign(ascmc[0])
        mc_sign, mc_deg = _longitude_to_sign(ascmc[1])

        try:
            birth_date = datetime.strptime(date, "%Y-%m-%d").date()
            is_future = birth_date > date_cls.today()
        except ValueError:
            is_future = False

        result = {
            "planets": planets,
            "houses": houses,
            "ascendant": {"sign": asc_sign, "degree": asc_deg, "longitude": round(ascmc[0], 4)},
            "midheaven": {"sign": mc_sign, "degree": mc_deg, "longitude": round(ascmc[1], 4)},
            "computed_for": {
                "date": date,
                "time": time,
                "lat": lat,
                "lng": lng,
                "timezone": timezone,
            },
        }
        if is_future:
            result["future_date"] = True
            result["note"] = (
                "This birth date is in the future, so the chart is speculative. "
                "Frame the reading as a possibility for who they may become, not as a lived chart."
            )
        return result

    except Exception as e:
        return {"error": f"Chart computation failed: {e}"}
