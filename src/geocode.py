"""Postcode -> geographic bounding box resolver using Nominatim (OSM)."""
import time
import requests
from config import NOMINATIM_URL, USER_AGENT, DEFAULT_STATE, DEFAULT_COUNTRY, NOMINATIM_RATE_LIMIT_SECONDS

_last_call = 0.0


def _rate_limit():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < NOMINATIM_RATE_LIMIT_SECONDS:
        time.sleep(NOMINATIM_RATE_LIMIT_SECONDS - elapsed)
    _last_call = time.time()


def geocode_postcode(postcode: str, state: str = DEFAULT_STATE, country: str = DEFAULT_COUNTRY) -> dict:
    """
    Resolve an Australian postcode to a bounding box + centroid via Nominatim.

    Returns dict: {postcode, display_name, lat, lon, bbox: {south, north, west, east}}
    Raises ValueError if not found.
    """
    _rate_limit()
    query = f"{postcode}, {state}, {country}"
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "jsonv2", "limit": 3, "addressdetails": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json()

    # Prefer a result actually tagged as a postcode / postal_code class, else take first.
    best = None
    for r in results:
        if r.get("addresstype") == "postcode" or r.get("class") == "boundary":
            best = r
            break
    if best is None and results:
        best = results[0]
    if best is None:
        raise ValueError(f"Postcode {postcode!r} in {state}, {country} not found via Nominatim.")

    south, north, west, east = map(float, best["boundingbox"])
    return {
        "postcode": postcode,
        "display_name": best.get("display_name"),
        "lat": float(best["lat"]),
        "lon": float(best["lon"]),
        "bbox": {"south": south, "north": north, "west": west, "east": east},
    }


if __name__ == "__main__":
    import sys, json
    pc = sys.argv[1] if len(sys.argv) > 1 else "3000"
    print(json.dumps(geocode_postcode(pc), indent=2))
