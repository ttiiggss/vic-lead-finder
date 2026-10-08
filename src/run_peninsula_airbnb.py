#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src to python path if run directly
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import discover
from boundaries import is_valid_postcode
from db import get_connection

PENINSULA_POSTCODES = [
    '3910', '3911', '3912', '3913', '3915', '3916', '3918', '3919', '3920', '3926',
    '3930', '3931', '3933', '3934', '3936', '3937', '3938', '3939', '3940', '3941',
    '3942', '3943', '3944'
]

def main():
    valid_pcs = [pc for pc in PENINSULA_POSTCODES if is_valid_postcode(pc)]
    print(f"Starting discovery of AirBNBs for {len(valid_pcs)} Peninsula postcodes...")
    
    for pc in valid_pcs:
        print(f"\n=================== POSTCODE {pc} ===================")
        try:
            discover.run(pc, ["airbnb"])
        except Exception as e:
            print(f"Error processing postcode {pc}: {e}")
            continue

    # Generate master summary from the local DB
    conn = get_connection()
    cur = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) "
        "FROM businesses WHERE category_key = 'airbnb' AND postcode IN (" + ",".join(["?"]*len(valid_pcs)) + ")",
        valid_pcs
    )
    total, has_phone, have_email = cur.fetchone()
    conn.close()

    print("\n==================================================")
    print("FINISHED PENINSULA DISCOVERY")
    print(f"Total AirBNBs / Holiday Rentals found: {total or 0}")
    print(f"  With Phone: {has_phone or 0}")
    print(f"  With Email: {have_email or 0}")
    print("==================================================")

if __name__ == "__main__":
    main()
