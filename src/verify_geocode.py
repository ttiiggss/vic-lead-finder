#!/usr/bin/env python3
"""
Post-process geocoded.jsonl to catch false-positive matches: cases where a
broad/generic fallback query (e.g. "CLUB HOTEL, Melbourne, Victoria") matched
a real but WRONG venue with a similar/generic name (confirmed case: "CLUB
HOTEL (FERNTREE GULLY)" matched "Central Club Hotel" in Richmond via Nominatim
fallback).

Strategy: compute a simple token-overlap similarity between the venue's own
name and the geocoded display_name. If similarity is too low AND the match
came from a broad fallback query (no LGA/suburb qualifier), flag it as
low_confidence rather than trust it silently. Low confidence matches are
excluded from the map/page by default in build_pokie_page.py -- listed but
unmapped, with a note to verify manually.
"""
import json
import re
from pathlib import Path

GEOCODED = Path("data/gaming/geocoded.jsonl")

STOPWORDS = {"the", "hotel", "club", "tavern", "taverner", "at", "on", "of", "and", "&", "resort", "inn"}


def tokenize(s):
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return {t for t in s.split() if t not in STOPWORDS and len(t) > 2}


def similarity(name, display_name):
    a = tokenize(name)
    b = tokenize(display_name or "")
    if not a:
        return 0.0
    return len(a & b) / len(a)


def main():
    records = [json.loads(l) for l in open(GEOCODED)]
    flagged = 0
    for rec in records:
        geo = rec.get("geo")
        if not geo:
            continue
        sim = similarity(rec["name"], geo.get("display_name"))
        query_used = rec.get("geo_query_used", "")
        is_broad_query = query_used and ("melbourne" in query_used.lower() or query_used.strip().upper() == rec["name"].strip().upper())
        # Flag as low confidence if token overlap is weak, regardless of query type,
        # since even "first pass" (LGA-qualified) queries can mismatch on generic names.
        low_conf = sim < 0.34
        rec["name_match_similarity"] = round(sim, 2)
        rec["low_confidence_match"] = low_conf
        if low_conf:
            flagged += 1
            print(f"LOW CONFIDENCE: {rec['name']!r} -> {geo.get('display_name')!r} (sim={sim:.2f}, query={query_used!r})")

    with open(GEOCODED, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"\n{flagged} matches flagged as low-confidence out of {sum(1 for r in records if r.get('geo'))} geocoded.")


if __name__ == "__main__":
    main()
