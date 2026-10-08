#!/usr/bin/env python3
import sqlite3
import csv
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "leads.db"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "by_postcode"

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get all postcodes
    cur = conn.execute("SELECT DISTINCT postcode FROM businesses WHERE postcode IS NOT NULL AND postcode != ''")
    postcodes = [row["postcode"] for row in cur.fetchall()]
    
    print(f"Exporting businesses for {len(postcodes)} postcodes...")
    fields = ["name", "category_label", "phone", "email", "website", "address",
              "suburb", "postcode", "postcode_source", "osm_tag", "consent_status"]
              
    for pc in postcodes:
        cur = conn.execute(
            f"SELECT {','.join(fields)} FROM businesses WHERE postcode=? ORDER BY category_label, name",
            (pc,)
        )
        rows = cur.fetchall()
        out_path = OUTPUT_DIR / f"{pc}.csv"
        
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            for row in rows:
                writer.writerow([row[fld] for fld in fields])
        print(f"  -> {len(rows)} rows written to {out_path.relative_to(OUTPUT_DIR.parent.parent)}")
        
    conn.close()

if __name__ == "__main__":
    main()
