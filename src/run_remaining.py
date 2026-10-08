#!/usr/bin/env python3
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import discover
from boundaries import is_valid_postcode
from db import get_connection

REMAINING_POSTCODES = [
    '3920', '3926', '3930', '3931', '3933', '3934', '3936', '3937', '3938', '3939',
    '3940', '3941', '3942', '3943', '3944'
]

def main():
    valid_pcs = [pc for pc in REMAINING_POSTCODES if is_valid_postcode(pc)]
    print(f"Starting discovery of AirBNBs for remaining {len(valid_pcs)} postcodes...")
    
    for pc in valid_pcs:
        print(f"\n=================== POSTCODE {pc} ===================")
        try:
            discover.run(pc, ["airbnb"])
        except Exception as e:
            print(f"Error processing postcode {pc}: {e}")
            continue

if __name__ == "__main__":
    main()
