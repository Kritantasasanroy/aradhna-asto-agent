from __future__ import annotations

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from langchain_core.tools import tool
from timezonefinder import TimezoneFinder

# one instance is fine — Nominatim asks for a unique user_agent string
_geocoder = Nominatim(user_agent="aradhna-astroagent/1.0")
_tf = TimezoneFinder()


@tool
def geocode_place(place_name: str) -> dict:
    """
    Resolve a place name to latitude, longitude, and timezone.

    Always call this before compute_birth_chart when you have a city name
    but not yet the coordinates. Uses OpenStreetMap — no API key needed.
    """
    try:
        location = _geocoder.geocode(place_name, timeout=10)
    except GeocoderTimedOut:
        return {"error": "Geocoding timed out. Try again in a moment."}
    except GeocoderServiceError as e:
        return {"error": f"Geocoding service unavailable: {e}"}

    if location is None:
        return {
            "error": (
                f"Could not find '{place_name}'. "
                "Ask the user to try a different spelling, a nearby major city, "
                "or add the country name (e.g. 'Chennai, India')."
            )
        }

    tz = _tf.timezone_at(lat=location.latitude, lng=location.longitude) or "UTC"

    return {
        "place": location.address,
        "lat": round(location.latitude, 6),
        "lng": round(location.longitude, 6),
        "timezone": tz,
    }
