#!/usr/bin/env python3
"""
Yellow Pages Australia Enrichment Tool.
Queries Yellow Pages listings slowly (with randomized delays) to retrieve business details,
phone numbers, and addresses for B&B listings.
"""
import sys
import re
import urllib.parse
import sqlite3
import time
import random
from pathlib import Path
import requests
from bs4 import BeautifulSoup

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "leads.db"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ponytail: simple slow scraper with random sleeps. Switch to headless browser automation if WAF blocking increases.
def search_yellowpages(business_name, location="Mornington Peninsula"):
    """
    Queries yellowpages.com.au search.
    Note: Yellow Pages uses heavy anti-scraping protections (Incapsula/Imperva).
    We use standard user-agent headers, standard accept headers, and referers to mimic organic traffic.
    """
    query = f"{business_name} {location}"
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.yellowpages.com.au/search/listings?clue={encoded_query}"
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.yellowpages.com.au/",
        "Connection": "keep-alive"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 403:
            print("    -> Blocked by Yellow Pages WAF (403 Forbidden).")
            return None
        if resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(resp.text, "html.parser")
        # Extract the first matching listing from search results
        listing = soup.find("div", class_="listing-card") or soup.find("div", class_="listing")
        if not listing:
            return None
            
        # Extract details
        name_elem = listing.find("a", class_="listing-name") or listing.find("h3")
        name = name_elem.get_text().strip() if name_elem else None
        
        phone_elem = listing.find("a", class_="contact-phone") or listing.find("span", class_="contact-text") or listing.find(class_=re.compile("phone", re.I))
        phone = phone_elem.get_text().strip() if phone_elem else None
        # Clean phone text
        if phone:
            phone = re.sub(r"\s+", " ", phone).strip()
            
        addr_elem = listing.find("p", class_="listing-address") or listing.find("span", class_="address") or listing.find(class_=re.compile("address", re.I))
        address = addr_elem.get_text().strip() if addr_elem else None
        if address:
            address = re.sub(r"\s+", " ", address).strip()
            
        return {"name": name, "phone": phone, "address": address}
    except Exception as e:
        print(f"    Yellow Pages search error: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Find Airbnb / B&B listings with missing phone details
    cur.execute(
        "SELECT osm_id, name, postcode FROM businesses WHERE category_key='airbnb' AND (phone IS NULL OR phone = '')"
    )
    rows = cur.fetchall()
    conn.close()
    
    print(f"Found {len(rows)} listings eligible for Yellow Pages enrichment.")
    
    success_count = 0
    for osm_id, name, postcode in rows:
        print(f"\nSearching Yellow Pages for: {name}...")
        
        # Clean name slightly
        clean_name = re.sub(r"[\-\u2014\u2013\u2022\u00b7].*$", "", name).strip()
        result = search_yellowpages(clean_name)
        
        if result and result["phone"]:
            print(f"  -> Found on Yellow Pages: {result['name']}")
            print(f"  -> Phone: {result['phone']}")
            if result['address']:
                print(f"  -> Address: {result['address']}")
                
            # Update database
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "UPDATE businesses SET phone=?, address=COALESCE(address, ?), source='yellowpages_enrichment', updated_at=datetime('now') WHERE osm_id=?",
                (result["phone"], result["address"], osm_id)
            )
            conn.commit()
            conn.close()
            success_count += 1
        else:
            print("  -> No listing or phone found.")
            
        # Slow, randomized sleep to avoid rate limiting and WAF triggers (5 to 15 seconds)
        sleep_time = random.uniform(5.0, 15.0)
        print(f"Sleeping for {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)
        
    print(f"\nYellow Pages enrichment completed. Successfully matched {success_count} listings.")

if __name__ == "__main__":
    main()
