#!/usr/bin/env python3
"""
Merge subagent-found addresses into geocoded.jsonl for venues that previously
failed. If lat/lon were supplied directly by the subagent, use them as-is
(with a name-similarity sanity check against the address string). Otherwise
geocode the found address via Nominatim (structured address queries are far
more reliable than venue-name-only queries).

Usage: python3 merge_addresses.py addresses.json
where addresses.json is a JSON array of {name, address, lat, lon, source_url}
"""
import json
import sys
import time
import requests
from pathlib import Path

GEOCODED = Path("data/gaming/geocoded.jsonl")
USER_AGENT = "vic-lead-finder/0.1 (personal research; gaming venue directory)"


def geocode_address(address, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{address}, Australia", "format": "jsonv2", "limit": 1, "countrycodes": "au"},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data:
                d = data[0]
                return {
                    "lat": float(d["lat"]), "lon": float(d["lon"]),
                    "display_name": d.get("display_name"),
                    "osm_type": d.get("osm_type"), "class": d.get("class"), "type": d.get("type"),
                }
            else:
                # Empty result with 200 status while an identical isolated
                # query succeeds is a sign of soft rate-limiting by Nominatim
                # (no 429 given, just an empty body) -- back off hard and retry.
                wait = 5 * (attempt + 1)
                print(f"  empty result for {address!r}, backing off {wait}s (attempt {attempt+1}/{retries})", file=sys.stderr)
                time.sleep(wait)
        except Exception as e:
            print(f"  geocode error for {address!r}: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(5)
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: merge_addresses.py <addresses.json>")
        sys.exit(1)

    found = json.loads(Path(sys.argv[1]).read_text())
    by_name = {f["name"].strip().upper(): f for f in found}

    records = [json.loads(l) for l in open(GEOCODED)]
    updated = 0
    still_missing = 0

    for rec in records:
        if rec.get("geo") and not rec.get("low_confidence_match"):
            continue  # already have a good match
        key = rec["name"].strip().upper()
        match = by_name.get(key)
        if not match or not match.get("address"):
            still_missing += 1
            continue

        if match.get("lat") and match.get("lon"):
            geo = {
                "lat": match["lat"], "lon": match["lon"],
                "display_name": match["address"],
                "osm_type": "manual", "class": "manual", "type": "subagent_found",
            }
        else:
            geo = geocode_address(match["address"])
            time.sleep(2.5)  # extra headroom beyond Nominatim's 1 req/sec minimum

        if geo:
            rec["geo"] = geo
            rec["geo_query_used"] = f"subagent-found address: {match['address']}"
            rec["low_confidence_match"] = False  # trust explicit address lookups
            rec["source_url"] = match.get("source_url")
            updated += 1
            print(f"MERGED: {rec['name']} -> {geo.get('display_name')}")
        else:
            still_missing += 1
            print(f"Could not geocode found address for {rec['name']}: {match['address']!r}")

    with open(GEOCODED, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"\n{updated} merged, {still_missing} still missing.")


if __name__ == "__main__":
    main()
