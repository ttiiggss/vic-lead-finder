#!/usr/bin/env python3
"""
Mirror-search enrichment: finds contact details for B&B/holiday-rental listings
by querying the local SearXNG instance, preferring directory-mirror domains that
republish Yellow Pages / White Pages / tourism-guide data (yellowpages itself 403s
all scripted traffic).

Route: listing name + town -> SearXNG query -> fetch top directory pages ->
regex-extract AU phone numbers + emails + first-party website.

Usage:
  python3 enrich_mirror.py                 # enrich DB airbnb rows missing phone
  python3 enrich_mirror.py --limit 20      # cap the batch
"""
import argparse
import random
import re
import sqlite3
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "leads.db"
SEARXNG = "http://localhost:8888/search"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# Directories that republish YP/WP/tourism-guide contact data
MIRROR_DOMAINS = [
    "yellowpages.com.au", "mymornington.directory", "australia.chamberofcommerce.com",
    "worldplaces.me", "cybo.com", "whereis.com", "localitybiz.com", "yellow.place",
    "peninsulapages.com", "your.pages.com.au", "hotelsinvictoria.net", "startuparound.com",
]
# Aggregators that never list host contacts
JUNK_DOMAINS = ["airbnb", "booking.com", "stayz", "vrbo", "tripadvisor", "expedia",
                "agoda", "traveloka", "trip.com", "facebook", "instagram", "wotif",
                "cheapholidayhomes", "lifeisoutside", "mapcarta", "hotelscombined"]

PHONE_RE = re.compile(r"(?:\+61|\(0\d\)|0)[\s-]?\d{4}[\s-]?\d{3,4}|0?4\d{2}[\s-]?\d{3}[\s-]?\d{3}")
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")


def searx(q, prefer_mirrors=True):
    params = {"q": q, "format": "json"}
    try:
        r = requests.get(SEARXNG, params=params, headers=UA, timeout=20)
        if r.status_code != 200:
            return []
        results = r.json().get("results", [])
    except Exception:
        return []
    if prefer_mirrors:
        mirrors = [x for x in results if any(d in x["url"] for d in MIRROR_DOMAINS)]
        clean = [x for x in mirrors + results if not any(d in x["url"] for d in JUNK_DOMAINS)]
        return clean
    return results


def fetch_extract(url):
    """Fetch a page, return (email, phone, website_candidates)."""
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200:
            return None, None
    except Exception:
        return None, None
    text = BeautifulSoup(r.text, "html.parser").get_text(separator=" ")
    # mailto: links beat body-text regex for reliability
    mailtos = re.findall(r"mailto:([^\"'?]+)", r.text)
    emails = [e for e in mailtos if EMAIL_RE.fullmatch(e.strip())] or EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    return (emails[0].strip() if emails else None,
            re.sub(r"\s+", " ", phones[0]).strip() if phones else None)


def enrich(name, town):
    """Return dict(website, email, phone) or None."""
    q = f'"{name}" {town}'
    hits = searx(q)
    if not hits:
        return None
    # 1st pass: fetch top 3 mirror/directory hits
    for hit in hits[:3]:
        email, phone = fetch_extract(hit["url"])
        if phone or email:
            return {"website": hit["url"], "email": email, "phone": phone}
    # 2nd pass: look for a first-party website domain in the remaining hits
    for hit in hits[:8]:
        url = hit["url"]
        if not any(d in url for d in MIRROR_DOMAINS + JUNK_DOMAINS):
            email, phone = fetch_extract(url)
            if phone or email:
                return {"website": url, "email": email, "phone": phone}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT osm_id, name, COALESCE(suburb,''), postcode FROM businesses "
        "WHERE category_key='airbnb' AND (phone IS NULL OR phone='') LIMIT ?",
        (args.limit,)).fetchall()

    print(f"Enriching {len(rows)} listings via mirror-search...")
    ok = 0
    for osm_id, name, suburb, postcode in rows:
        town = suburb or "Mornington Peninsula"
        print(f"\n>> {name} ({town})")
        res = enrich(name, town)
        if res and (res["phone"] or res["email"]):
            print(f"   phone={res['phone']} email={res['email']} site={res['website']}")
            conn.execute(
                "UPDATE businesses SET phone=COALESCE(?,phone), email=COALESCE(?,email), "
                "website=COALESCE(?,website), source='mirror_search', "
                "updated_at=datetime('now') WHERE osm_id=?",
                (res["phone"], res["email"], res["website"], osm_id))
            conn.commit()
            ok += 1
        else:
            print("   no contact found")
        time.sleep(random.uniform(3, 6))  # ponytail: fixed modest delay; add proxy rotation if mirrors start blocking

    conn.close()
    print(f"\nDone: {ok}/{len(rows)} enriched.")


if __name__ == "__main__":
    main()
