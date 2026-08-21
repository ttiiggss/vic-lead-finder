#!/usr/bin/env python3
"""
VIC Lead Finder CLI (Phase 1 - discovery only, no outreach).

Usage:
  python3 discover.py --postcode 3121 --categories electrician,plumber,builder
  python3 discover.py --postcode 3121 --all-categories
  python3 discover.py --list-categories

Data source: OpenStreetMap via Nominatim (geocoding) + Overpass API (business
search). This deliberately avoids bulk use of the Google Places API, whose
Terms of Service prohibit building an independent stored database of places
from its data. See NOTES.md for details and the optional shortlist-only
Google enrichment step.

Output: writes/updates data/leads.db (SQLite) and exports a CSV shortlist to
output/<postcode>_<timestamp>.csv for human review.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from fetch import fetch_categories
from categories import list_category_keys, get_categories
from db import get_connection
from store import store_records, log_fetch
from boundaries import get_postcode_bbox, point_in_postcode, is_valid_postcode

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def run(postcode: str, category_keys: list[str], strict_postcode: bool = False):
    print(f"[1/4] Resolving postcode {postcode} boundary via ABS POA 2021 (official gov boundary)...")
    if not is_valid_postcode(postcode):
        print(f"      -> ERROR: {postcode} not found in ABS Postal Areas dataset. "
              f"Check it's a valid Australian postcode.")
        sys.exit(1)
    bbox = get_postcode_bbox(postcode)
    print(f"      -> tight bbox: {bbox}")

    def polygon_filter(lat, lon):
        return point_in_postcode(lat, lon, postcode)

    print(f"[2/4] Querying Overpass for {len(category_keys)} categories: {', '.join(category_keys)}")
    results = fetch_categories(bbox, category_keys, target_postcode=postcode,
                                strict_postcode=strict_postcode, polygon_filter=polygon_filter)

    all_records = []
    for key, recs in results.items():
        print(f"      -> {key}: {len(recs)} businesses found")
        all_records.extend(recs)

    print(f"[3/4] Storing {len(all_records)} records in local DB (dedup on OSM id)...")
    conn = get_connection()
    stats = store_records(conn, all_records)
    log_fetch(conn, postcode, category_keys, bbox, len(all_records))
    print(f"      -> inserted: {stats['inserted']}, updated: {stats['updated']}")

    print("[4/4] Exporting review CSV...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{postcode}_{ts}.csv"
    fields = ["name", "category_label", "phone", "email", "website", "address",
              "suburb", "postcode", "postcode_source", "osm_tag", "consent_status"]
    cur = conn.execute(
        f"SELECT {','.join(fields)} FROM businesses WHERE postcode=? ORDER BY category_label, name",
        (postcode,),
    )
    rows = cur.fetchall()
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for row in rows:
            writer.writerow([row[fld] for fld in fields])
    print(f"      -> {len(rows)} rows written to {out_path}")

    # quick contactability summary
    have_phone = sum(1 for r in rows if r["phone"])
    have_email = sum(1 for r in rows if r["email"])
    have_website = sum(1 for r in rows if r["website"])
    bbox_estimated = sum(1 for r in rows if r["postcode_source"] == "bbox_estimate")
    print("\n--- Summary ---")
    print(f"Total businesses in postcode {postcode} (confirmed inside real ABS polygon): {len(rows)}")
    print(f"  with phone:   {have_phone}")
    print(f"  with email:   {have_email}")
    print(f"  with website: {have_website}")
    print(f"  no explicit OSM addr:postcode tag (postcode inferred from search area, but geo-confirmed inside polygon): {bbox_estimated}")
    print(f"\nReminder: consent_status defaults to 'not_contacted'. No outreach")
    print(f"has been sent. Review {out_path} before any Phase 2 consent-gate work.")
    conn.close()
    return out_path


def main():
    parser = argparse.ArgumentParser(description="VIC postcode business discovery (Phase 1)")
    parser.add_argument("--postcode", help="4-digit Victorian postcode, e.g. 3121")
    parser.add_argument("--categories", help="Comma-separated category keys (see --list-categories)")
    parser.add_argument("--all-categories", action="store_true", help="Fetch every known category")
    parser.add_argument("--strict-postcode", action="store_true",
                         help="Drop results whose OSM addr:postcode tag is present but doesn't match target (default: keep, since most POIs lack this tag)")
    parser.add_argument("--list-categories", action="store_true", help="List available category keys and exit")
    args = parser.parse_args()

    if args.list_categories:
        for k, v in get_categories().items():
            print(f"  {k:20s} {v['label']}")
        return

    if not args.postcode:
        parser.error("--postcode is required (or use --list-categories)")

    if args.all_categories:
        cats = list_category_keys()
    elif args.categories:
        cats = [c.strip() for c in args.categories.split(",")]
        unknown = [c for c in cats if c not in list_category_keys()]
        if unknown:
            parser.error(f"Unknown category keys: {unknown}. Run --list-categories to see valid keys.")
    else:
        parser.error("Specify --categories or --all-categories")

    run(args.postcode, cats, strict_postcode=args.strict_postcode)


if __name__ == "__main__":
    main()
