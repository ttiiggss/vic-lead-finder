#!/usr/bin/env python3
"""Retry pass for venues that failed to geocode on the first pass, using
smarter query variants (handles parenthetical suburb hints, strips noisy
words, falls back to broader queries)."""
import json
import re
import time
import sys
import requests
from pathlib import Path

GEOCODED = Path("data/gaming/geocoded.jsonl")
USER_AGENT = "vic-lead-finder/0.1 (personal research; gaming venue directory)"


def geocode(query):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "au"},
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
    except Exception as e:
        print(f"  ERROR {query!r}: {e}", file=sys.stderr)
    return None


def build_query_variants(name, lga):
    lga_clean = lga.replace("City of ", "").replace("Shire of ", "")
    variants = []

    # Extract parenthetical suburb hint e.g. "GRAND HOTEL (FRANKSTON)"
    m = re.search(r"\(([^)]+)\)", name)
    base_name = re.sub(r"\s*\([^)]+\)", "", name).strip()
    if m:
        suburb_hint = m.group(1).strip()
        variants.append(f"{base_name}, {suburb_hint}, Victoria, Australia")
        variants.append(f"{base_name} Hotel, {suburb_hint}, Victoria, Australia")

    # Strip noisy trade-specific words that aren't real OSM names
    stripped = re.sub(r"\bTAVERNER\b", "Tavern", base_name, flags=re.I)
    if stripped != base_name:
        variants.append(f"{stripped}, {lga_clean}, Victoria, Australia")
        variants.append(f"{stripped}, Victoria, Australia")

    # Broad fallback: just name + Melbourne
    variants.append(f"{base_name}, Melbourne, Victoria, Australia")
    variants.append(f"{base_name}, Victoria, Australia")

    # last resort: base name only
    variants.append(base_name)

    # de-dup preserving order
    seen = set()
    out = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def main():
    records = [json.loads(l) for l in open(GEOCODED)]
    updated = 0
    for i, rec in enumerate(records):
        if rec.get("geo"):
            continue
        variants = build_query_variants(rec["name"], rec["lga"])
        for q in variants:
            geo = geocode(q)
            time.sleep(1.1)
            if geo:
                rec["geo"] = geo
                rec["geo_query_used"] = q
                updated += 1
                print(f"[{i+1}] {rec['name']} -> FOUND via {q!r}")
                break
        else:
            print(f"[{i+1}] {rec['name']} -> still not found after {len(variants)} variants")

    with open(GEOCODED, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    still_missing = sum(1 for r in records if not r.get("geo"))
    print(f"\nRetry pass: {updated} newly geocoded. {still_missing} still missing out of {len(records)}.")


if __name__ == "__main__":
    main()
