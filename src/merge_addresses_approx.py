#!/usr/bin/env python3
"""
Fallback merge: when Nominatim is rate-limiting us, use the ABS POA postcode
polygon centroid as an APPROXIMATE map location (clearly labeled as such)
rather than leaving the venue with no address at all. This gets a trustworthy
address string into the table immediately; precise pin-point coordinates can
be backfilled later via a slower Nominatim pass once any rate limit clears.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")
from boundaries import get_postcode_bbox, is_valid_postcode

GEOCODED = Path("data/gaming/geocoded.jsonl")


def extract_postcode(address):
    m = re.search(r"\b(3\d{3})\b", address)
    return m.group(1) if m else None


def main(addr_file):
    found = json.loads(Path(addr_file).read_text())
    by_name = {f["name"].strip().upper(): f for f in found}

    records = [json.loads(l) for l in open(GEOCODED)]
    updated = 0
    for rec in records:
        if rec.get("geo") and not rec.get("low_confidence_match"):
            continue
        key = rec["name"].strip().upper()
        match = by_name.get(key)
        if not match or not match.get("address"):
            continue

        pc = extract_postcode(match["address"])
        if not pc or not is_valid_postcode(pc):
            print(f"SKIP {rec['name']}: could not extract valid postcode from {match['address']!r}")
            continue

        bbox = get_postcode_bbox(pc)
        centroid_lat = (bbox["north"] + bbox["south"]) / 2
        centroid_lon = (bbox["east"] + bbox["west"]) / 2

        rec["geo"] = {
            "lat": centroid_lat, "lon": centroid_lon,
            "display_name": match["address"],
            "osm_type": "approximate", "class": "approximate", "type": "postcode_centroid",
        }
        rec["geo_query_used"] = f"subagent-found address (postcode-centroid approx, Nominatim unavailable): {match['address']}"
        rec["low_confidence_match"] = False
        rec["approximate_location"] = True  # NEW flag: precise address known, but pin is postcode-centroid only
        rec["source_url"] = match.get("source_url")
        updated += 1
        print(f"APPROX: {rec['name']} -> {match['address']} (pin = postcode {pc} centroid)")

    with open(GEOCODED, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"\n{updated} venues given approximate (postcode-centroid) locations with real addresses.")


if __name__ == "__main__":
    main(sys.argv[1])
