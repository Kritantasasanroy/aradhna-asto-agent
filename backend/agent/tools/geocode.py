from __future__ import annotations

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from langchain_core.tools import tool
from timezonefinder import TimezoneFinder

_geocoder = Nominatim(user_agent="aradhna-astroagent/1.0")
_tf = TimezoneFinder()

# Country or continent level is too broad — the centroid could be hundreds of
# miles from the actual birth city, making house cusps meaningless.
_TOO_BROAD = {"country", "continent"}

# These are countries that are essentially a single city — no need to ask
# someone from Singapore "which city were you born in?"
_CITY_STATES = {
    "singapore", "monaco", "vatican", "vatican city", "hong kong",
    "macau", "macao", "san marino", "gibraltar", "bahrain", "malta",
}

# Major cities resolved locally so the tool works even when Nominatim is
# unavailable (it enforces 1 req/sec and temporarily blocks burst access).
# Keys are bare lowercase city names with no country suffix.
_CITY_CACHE: dict[str, tuple[float, float, str]] = {
    # South Asia
    "mumbai": (19.0760, 72.8777, "Asia/Kolkata"),
    "bombay": (19.0760, 72.8777, "Asia/Kolkata"),
    "delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "new delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "chennai": (13.0827, 80.2707, "Asia/Kolkata"),
    "madras": (13.0827, 80.2707, "Asia/Kolkata"),
    "bangalore": (12.9716, 77.5946, "Asia/Kolkata"),
    "bengaluru": (12.9716, 77.5946, "Asia/Kolkata"),
    "kolkata": (22.5726, 88.3639, "Asia/Kolkata"),
    "calcutta": (22.5726, 88.3639, "Asia/Kolkata"),
    "hyderabad": (17.3850, 78.4867, "Asia/Kolkata"),
    "jaipur": (26.9124, 75.7873, "Asia/Kolkata"),
    "pune": (18.5204, 73.8567, "Asia/Kolkata"),
    "ahmedabad": (23.0225, 72.5714, "Asia/Kolkata"),
    "karachi": (24.8607, 67.0011, "Asia/Karachi"),
    "lahore": (31.5204, 74.3587, "Asia/Karachi"),
    "dhaka": (23.8103, 90.4125, "Asia/Dhaka"),
    "colombo": (6.9271, 79.8612, "Asia/Colombo"),
    "kathmandu": (27.7172, 85.3240, "Asia/Kathmandu"),
    # East & Southeast Asia
    "tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
    "osaka": (34.6937, 135.5023, "Asia/Tokyo"),
    "beijing": (39.9042, 116.4074, "Asia/Shanghai"),
    "peking": (39.9042, 116.4074, "Asia/Shanghai"),
    "shanghai": (31.2304, 121.4737, "Asia/Shanghai"),
    "hong kong": (22.3193, 114.1694, "Asia/Hong_Kong"),
    "singapore": (1.3521, 103.8198, "Asia/Singapore"),
    "bangkok": (13.7563, 100.5018, "Asia/Bangkok"),
    "seoul": (37.5665, 126.9780, "Asia/Seoul"),
    "jakarta": (-6.2088, 106.8456, "Asia/Jakarta"),
    "kuala lumpur": (3.1390, 101.6869, "Asia/Kuala_Lumpur"),
    "manila": (14.5995, 120.9842, "Asia/Manila"),
    "ho chi minh city": (10.8231, 106.6297, "Asia/Ho_Chi_Minh"),
    # Middle East
    "dubai": (25.2048, 55.2708, "Asia/Dubai"),
    "abu dhabi": (24.4539, 54.3773, "Asia/Dubai"),
    "tehran": (35.6892, 51.3890, "Asia/Tehran"),
    "riyadh": (24.7136, 46.6753, "Asia/Riyadh"),
    "istanbul": (41.0082, 28.9784, "Europe/Istanbul"),
    # Europe
    "london": (51.5074, -0.1278, "Europe/London"),
    "paris": (48.8566, 2.3522, "Europe/Paris"),
    "berlin": (52.5200, 13.4050, "Europe/Berlin"),
    "rome": (41.9028, 12.4964, "Europe/Rome"),
    "madrid": (40.4168, -3.7038, "Europe/Madrid"),
    "barcelona": (41.3874, 2.1686, "Europe/Madrid"),
    "amsterdam": (52.3676, 4.9041, "Europe/Amsterdam"),
    "dublin": (53.3498, -6.2603, "Europe/Dublin"),
    "lisbon": (38.7223, -9.1393, "Europe/Lisbon"),
    "vienna": (48.2082, 16.3738, "Europe/Vienna"),
    "zurich": (47.3769, 8.5417, "Europe/Zurich"),
    "moscow": (55.7558, 37.6173, "Europe/Moscow"),
    "stockholm": (59.3293, 18.0686, "Europe/Stockholm"),
    "athens": (37.9838, 23.7275, "Europe/Athens"),
    # North America
    "new york": (40.7128, -74.0060, "America/New_York"),
    "new york city": (40.7128, -74.0060, "America/New_York"),
    "chicago": (41.8781, -87.6298, "America/Chicago"),
    "los angeles": (34.0522, -118.2437, "America/Los_Angeles"),
    "san francisco": (37.7749, -122.4194, "America/Los_Angeles"),
    "boston": (42.3601, -71.0589, "America/New_York"),
    "washington": (38.9072, -77.0369, "America/New_York"),
    "seattle": (47.6062, -122.3321, "America/Los_Angeles"),
    "miami": (25.7617, -80.1918, "America/New_York"),
    "houston": (29.7604, -95.3698, "America/Chicago"),
    "atlanta": (33.7490, -84.3880, "America/New_York"),
    "toronto": (43.6532, -79.3832, "America/Toronto"),
    "vancouver": (49.2827, -123.1207, "America/Vancouver"),
    "montreal": (45.5019, -73.5674, "America/Toronto"),
    "mexico city": (19.4326, -99.1332, "America/Mexico_City"),
    # South America
    "sao paulo": (-23.5505, -46.6333, "America/Sao_Paulo"),
    "rio de janeiro": (-22.9068, -43.1729, "America/Sao_Paulo"),
    "buenos aires": (-34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    "lima": (-12.0464, -77.0428, "America/Lima"),
    "bogota": (4.7110, -74.0721, "America/Bogota"),
    "santiago": (-33.4489, -70.6693, "America/Santiago"),
    # Africa
    "cairo": (30.0444, 31.2357, "Africa/Cairo"),
    "lagos": (6.5244, 3.3792, "Africa/Lagos"),
    "johannesburg": (-26.2041, 28.0473, "Africa/Johannesburg"),
    "cape town": (-33.9249, 18.4241, "Africa/Johannesburg"),
    "nairobi": (-1.2864, 36.8172, "Africa/Nairobi"),
    "casablanca": (33.5731, -7.5898, "Africa/Casablanca"),
    # Oceania
    "sydney": (-33.8688, 151.2093, "Australia/Sydney"),
    "melbourne": (-37.8136, 144.9631, "Australia/Melbourne"),
    "brisbane": (-27.4698, 153.0251, "Australia/Brisbane"),
    "perth": (-31.9505, 115.8605, "Australia/Perth"),
    "auckland": (-36.8485, 174.7633, "Pacific/Auckland"),
}


@tool
def geocode_place(place_name: str) -> dict:
    """
    Resolve a place name to latitude, longitude, and timezone.

    Call this before compute_birth_chart whenever you have a city name but not
    yet the coordinates. Well-known cities resolve from a built-in table
    instantly; everything else looks up OpenStreetMap (no API key needed).

    Returns {"ambiguous": true} if the place is a whole country or continent —
    ask the user for a specific city in that case.
    """
    key = place_name.strip().lower()

    # Check the local cache first. Only match bare city names (no comma) so
    # "Paris, Texas" still goes to Nominatim instead of matching Paris France.
    if "," not in place_name and key in _CITY_CACHE:
        lat, lng, tz = _CITY_CACHE[key]
        return {
            "place": place_name.strip().title(),
            "lat": lat,
            "lng": lng,
            "timezone": tz,
        }

    try:
        location = _geocoder.geocode(place_name, timeout=10, addressdetails=True)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return {
            "error": (
                f"Place lookup is temporarily unavailable ({type(e).__name__}). "
                "Ask the user to try again in a moment, or suggest a nearby major city."
            )
        }

    if location is None:
        return {
            "error": (
                f"Could not find '{place_name}'. "
                "Ask the user to try a different spelling, a nearby major city, "
                "or add the country name (e.g. 'Chennai, India')."
            )
        }

    addresstype = (location.raw.get("addresstype") or "").lower()
    is_city_state = key in _CITY_STATES
    if addresstype in _TOO_BROAD and not is_city_state:
        return {
            "ambiguous": True,
            "matched": location.address,
            "addresstype": addresstype,
            "message": (
                f"'{place_name}' resolved to a whole {addresstype}, which is too broad "
                "for an accurate chart. Ask the user for the specific city or town of "
                "birth — the rising sign and houses depend on the exact location."
            ),
        }

    tz = _tf.timezone_at(lat=location.latitude, lng=location.longitude) or "UTC"

    return {
        "place": location.address,
        "lat": round(location.latitude, 6),
        "lng": round(location.longitude, 6),
        "timezone": tz,
    }
