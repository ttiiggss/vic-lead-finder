"""
Authoritative Australian postcode boundary lookup using the ABS ASGS
Postal Areas (POA) 2021 shapefile -- NOT Nominatim's point/bbox guess.

Optimized with indexing and single-shape parsing for high-performance lookups.
"""
from pathlib import Path
from functools import lru_cache

import shapefile
from shapely.geometry import shape, Point

SHP_PATH = Path(__file__).resolve().parent.parent / "data" / "boundaries" / "POA_2021" / "POA_2021_AUST_GDA2020.shp"


@lru_cache(maxsize=1)
def _load_shapefile():
    if not SHP_PATH.exists():
        raise FileNotFoundError(
            f"POA shapefile not found at {SHP_PATH}. Download it from ABS:\n"
            "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/"
            "edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/"
            "POA_2021_AUST_GDA2020_SHP.zip"
        )
    return shapefile.Reader(str(SHP_PATH))


@lru_cache(maxsize=1)
def _load_and_index_poas():
    sf = _load_shapefile()
    # sf.records() only reads DBF metadata (very fast), avoiding heavy shape coordinate parsing
    poa_index = {rec["POA_CODE21"]: idx for idx, rec in enumerate(sf.records())}
    return sf, poa_index


@lru_cache(maxsize=4000)
def get_postcode_polygon(postcode: str):
    """Return a shapely geometry for the given 4-digit postcode, or None if not found."""
    sf, poa_index = _load_and_index_poas()
    if postcode in poa_index:
        idx = poa_index[postcode]
        # sf.shape(idx) parses ONLY the requested shape geometry, which is incredibly fast
        return shape(sf.shape(idx).__geo_interface__)
    return None


def get_postcode_bbox(postcode: str) -> dict:
    """Return a tight bounding box {south, north, west, east} from the real polygon."""
    geom = get_postcode_polygon(postcode)
    if geom is None:
        raise ValueError(f"Postcode {postcode!r} not found in ABS POA 2021 dataset.")
    minx, miny, maxx, maxy = geom.bounds
    return {"south": miny, "north": maxy, "west": minx, "east": maxx}


def point_in_postcode(lat: float, lon: float, postcode: str) -> bool:
    """True if (lat, lon) falls inside the given postcode's real polygon."""
    geom = get_postcode_polygon(postcode)
    if geom is None:
        return False
    return geom.contains(Point(lon, lat))


def is_valid_postcode(postcode: str) -> bool:
    sf, poa_index = _load_and_index_poas()
    return postcode in poa_index


if __name__ == "__main__":
    import sys
    pc = sys.argv[1] if len(sys.argv) > 1 else "3121"
    bbox = get_postcode_bbox(pc)
    print(f"Postcode {pc} tight bbox (from real ABS polygon): {bbox}")
    lat_span = bbox["north"] - bbox["south"]
    lon_span = bbox["east"] - bbox["west"]
    print(f"  span: {lat_span:.4f} lat x {lon_span:.4f} lon")
