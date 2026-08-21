"""Overpass API fetch layer: query OSM for businesses matching category tags
within a bounding box, normalize, and return structured records.
"""
import time
import requests
from config import OVERPASS_URLS, USER_AGENT, OVERPASS_RATE_LIMIT_SECONDS
from categories import get_categories

_last_call = 0.0


def _rate_limit():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < OVERPASS_RATE_LIMIT_SECONDS:
        time.sleep(OVERPASS_RATE_LIMIT_SECONDS - elapsed)
    _last_call = time.time()


def _build_query(bbox: dict, osm_filters: list[str]) -> str:
    """Build an Overpass QL query for a set of tag filter strings like
    'shop=electrical' or 'shop~"electronics|hardware"', within a bbox."""
    south, west, north, east = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    clauses = []
    for filt in osm_filters:
        if "~" in filt:
            key, val = filt.split("~", 1)
            tagfilter = f'["{key}"~{val}]'
        else:
            key, val = filt.split("=", 1)
            tagfilter = f'["{key}"="{val}"]'
        clauses.append(f'  nwr{tagfilter}({south:.7f},{west:.7f},{north:.7f},{east:.7f});')
    body = "\n".join(clauses)
    return f"[out:json][timeout:90];\n(\n{body}\n);\nout center tags;"


def _run_overpass(query: str) -> dict:
    _rate_limit()
    last_err = None
    # Try the primary endpoint with several retries first (it's generally the
    # most reliable); only fall back to mirrors after primary is exhausted.
    for url_index, url in enumerate(OVERPASS_URLS):
        attempts = 3 if url_index == 0 else 1
        for attempt in range(attempts):
            try:
                resp = requests.post(
                    url,
                    data=query.encode("utf-8"),
                    headers={"User-Agent": USER_AGENT},
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                time.sleep(3 * (attempt + 1))
                continue
    raise RuntimeError(f"All Overpass endpoints failed after retries. Last error: {last_err}")


def _extract_contact(tags: dict) -> dict:
    phone = tags.get("contact:phone") or tags.get("phone") or tags.get("contact:mobile") or tags.get("mobile")
    email = tags.get("contact:email") or tags.get("email")
    website = tags.get("contact:website") or tags.get("website") or tags.get("contact:facebook")
    addr_parts = []
    for k in ("addr:housenumber", "addr:street"):
        if tags.get(k):
            addr_parts.append(tags[k])
    address = " ".join(addr_parts) if addr_parts else None
    postcode = tags.get("addr:postcode")
    suburb = tags.get("addr:suburb") or tags.get("addr:city")
    return {
        "phone": phone,
        "email": email,
        "website": website,
        "address": address,
        "postcode": postcode,
        "suburb": suburb,
    }


def fetch_category(bbox: dict, category_key: str, target_postcode: str | None = None,
                    strict_postcode: bool = False, polygon_filter=None) -> list[dict]:
    """Fetch all OSM elements matching one category's tag filters within bbox.
    Returns a list of normalized dicts ready for DB insertion.

    bbox should be the TIGHT bbox from boundaries.get_postcode_bbox() (ABS POA
    polygon), not Nominatim's oversized point-based guess.

    polygon_filter: optional callable(lat, lon) -> bool. When given, elements
    outside the real postcode polygon are dropped even if they fall inside
    the rectangular bbox (bbox always over-includes near polygon corners).
    Use boundaries.point_in_postcode for this.
    """
    cats = get_categories([category_key])
    if not cats:
        raise ValueError(f"Unknown category key: {category_key}")
    cat = cats[category_key]
    query = _build_query(bbox, cat["osm_filters"])
    data = _run_overpass(query)

    records = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue  # skip unnamed nodes -- not useful leads
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")

        if polygon_filter is not None and lat is not None and lon is not None:
            if not polygon_filter(lat, lon):
                continue  # outside the real postcode polygon, just inside bbox corner

        # figure out which tag actually matched, for provenance
        matched_tag = None
        for filt in cat["osm_filters"]:
            key = filt.split("=")[0].split("~")[0]
            if key in tags:
                matched_tag = f"{key}={tags[key]}"
                break

        contact = _extract_contact(tags)

        if strict_postcode and target_postcode and contact["postcode"] and contact["postcode"] != target_postcode:
            continue

        postcode_source = "osm_tag" if contact["postcode"] else "bbox_estimate"
        if not contact["postcode"] and target_postcode:
            contact["postcode"] = target_postcode  # best-effort fill from search target

        records.append({
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "name": name,
            "category_key": category_key,
            "category_label": cat["label"],
            "osm_tag": matched_tag,
            "lat": lat,
            "lon": lon,
            "postcode_source": postcode_source,
            **contact,
        })
    return records


def fetch_categories(bbox: dict, category_keys: list[str], target_postcode: str | None = None,
                      strict_postcode: bool = False, polygon_filter=None) -> dict[str, list[dict]]:
    """Fetch multiple categories, one Overpass call each (rate-limited)."""
    results = {}
    for key in category_keys:
        results[key] = fetch_category(bbox, key, target_postcode=target_postcode,
                                       strict_postcode=strict_postcode, polygon_filter=polygon_filter)
    return results


if __name__ == "__main__":
    import sys, json
    from geocode import geocode_postcode
    pc = sys.argv[1] if len(sys.argv) > 1 else "3000"
    cat = sys.argv[2] if len(sys.argv) > 2 else "cafe"
    geo = geocode_postcode(pc)
    recs = fetch_category(geo["bbox"], cat)
    print(f"Found {len(recs)} '{cat}' businesses in postcode {pc}")
    print(json.dumps(recs[:5], indent=2))
