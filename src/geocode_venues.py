#!/usr/bin/env python3
"""
Geocode metro gaming venues from VGCCC data using Nominatim.
Resumable: writes progress to geocoded.jsonl as it goes, skips already-done venues.
"""
import json
import time
import sys
import requests
from pathlib import Path

RAW = Path("data/gaming/metro_venues_raw.json")
OUT = Path("data/gaming/geocoded.jsonl")
USER_AGENT = "vic-lead-finder/0.1 (personal research; gaming venue directory)"

LGA_TO_REGION_HINT = {}  # not used, kept simple


def load_done():
    done = {}
    if OUT.exists():
        with open(OUT) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                done[rec["name"]] = rec
    return done


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
                "lat": float(d["lat"]),
                "lon": float(d["lon"]),
                "display_name": d.get("display_name"),
                "osm_type": d.get("osm_type"),
                "class": d.get("class"),
                "type": d.get("type"),
            }
    except Exception as e:
        print(f"  ERROR geocoding {query!r}: {e}", file=sys.stderr)
    return None


def main():
    raw = json.loads(RAW.read_text())
    done = load_done()
    print(f"{len(raw)} venues total, {len(done)} already geocoded")

    with open(OUT, "a") as out:
        for i, venue in enumerate(raw):
            name = venue["name"]
            if name in done:
                continue
            lga_clean = venue["lga"].replace("City of ", "").replace("Shire of ", "")
            query = f"{name}, {lga_clean}, Victoria, Australia"
            geo = geocode(query)
            time.sleep(1.1)  # Nominatim usage policy: max 1 req/sec

            if geo is None:
                # retry with a simpler query (name + Victoria only)
                query2 = f"{name}, Victoria, Australia"
                geo = geocode(query2)
                time.sleep(1.1)

            record = {**venue, "geo": geo}
            out.write(json.dumps(record) + "\n")
            out.flush()
            status = "OK" if geo else "NOT FOUND"
            print(f"[{i+1}/{len(raw)}] {name} -> {status}")

    print("Done.")


if __name__ == "__main__":
    main()
