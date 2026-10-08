"""Config constants for VIC Lead Finder."""

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

USER_AGENT = "vic-lead-finder/0.1 (personal business tooling; non-commercial research use)"

# Nominatim usage policy: max 1 request/sec, must set a real UA.
NOMINATIM_RATE_LIMIT_SECONDS = 1.1
OVERPASS_RATE_LIMIT_SECONDS = 2.0

DEFAULT_STATE = "Victoria"
DEFAULT_COUNTRY = "Australia"
