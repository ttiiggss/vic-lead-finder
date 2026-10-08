"""
Business category mapping: maps a human-readable category label to the OSM
tag(s) that identify it, and (for reference/QA only) the equivalent Google
Places 'type' string. Extend this table to match YOUR company's target
customer categories -- this is the main file you edit per-campaign.

OSM tagging reference: https://wiki.openstreetmap.org/wiki/Map_features
Google Place Types reference: https://developers.google.com/maps/documentation/places/web-service/place-types

Each entry:
  key -> {
    "label": human readable name,
    "osm_filters": list of Overpass tag-filter strings, e.g. 'shop=electronics'
                   or 'shop~"electronics|hardware"' (regex form),
    "google_type": equivalent Google Places primary type (reference only,
                   NOT used for bulk fetching -- see enrich.py docstring),
  }
"""

CATEGORIES = {
    "electrician": {
        "label": "Electrician",
        "osm_filters": ['craft=electrician', 'shop=electrical'],
        "google_type": "electrician",
    },
    "plumber": {
        "label": "Plumber",
        "osm_filters": ['craft=plumber'],
        "google_type": "plumber",
    },
    "hvac": {
        "label": "HVAC / Air Conditioning",
        "osm_filters": ['craft=hvac', 'shop=hvac'],
        "google_type": "hvac_contractor",
    },
    "builder": {
        "label": "Builder / General Contractor",
        "osm_filters": ['craft=builder', 'office=construction_company'],
        "google_type": "general_contractor",
    },
    "cafe": {
        "label": "Cafe",
        "osm_filters": ['amenity=cafe'],
        "google_type": "cafe",
    },
    "restaurant": {
        "label": "Restaurant",
        "osm_filters": ['amenity=restaurant'],
        "google_type": "restaurant",
    },
    "hairdresser": {
        "label": "Hairdresser / Salon",
        "osm_filters": ['shop=hairdresser'],
        "google_type": "hair_salon",
    },
    "beauty_salon": {
        "label": "Beauty Salon",
        "osm_filters": ['shop=beauty'],
        "google_type": "beauty_salon",
    },
    "gym": {
        "label": "Gym / Fitness",
        "osm_filters": ['leisure=fitness_centre', 'sport=fitness'],
        "google_type": "gym",
    },
    "real_estate": {
        "label": "Real Estate Agency",
        "osm_filters": ['office=estate_agent'],
        "google_type": "real_estate_agency",
    },
    "accounting": {
        "label": "Accounting / Bookkeeping",
        "osm_filters": ['office=accountant'],
        "google_type": "accounting",
    },
    "law_firm": {
        "label": "Law Firm",
        "osm_filters": ['office=lawyer'],
        "google_type": "lawyer",
    },
    "car_repair": {
        "label": "Car Repair / Mechanic",
        "osm_filters": ['shop=car_repair'],
        "google_type": "car_repair",
    },
    "dentist": {
        "label": "Dentist",
        "osm_filters": ['amenity=dentist'],
        "google_type": "dentist",
    },
    "physiotherapy": {
        "label": "Physiotherapy",
        "osm_filters": ['healthcare=physiotherapist', 'amenity=clinic'],
        "google_type": "physiotherapist",
    },
    "retail_general": {
        "label": "General Retail",
        "osm_filters": ['shop=yes', 'shop=general', 'shop=variety_store'],
        "google_type": "store",
    },
    "hardware_store": {
        "label": "Hardware Store",
        "osm_filters": ['shop=hardware', 'shop=doityourself'],
        "google_type": "hardware_store",
    },
    "office_generic": {
        "label": "Generic Office / Professional Services",
        "osm_filters": ['office=company', 'office=yes'],
        "google_type": "corporate_office",
    },
    "airbnb": {
        "label": "AirBNB / Holiday Rental",
        "osm_filters": ['tourism=apartment', 'tourism=chalet', 'tourism=guest_house', 'tourism=cottage'],
        "google_type": "lodging",
    },
}


def get_categories(keys=None):
    """Return the category dicts for the given keys, or all if keys is None."""
    if keys is None:
        return CATEGORIES
    return {k: CATEGORIES[k] for k in keys if k in CATEGORIES}


def list_category_keys():
    return list(CATEGORIES.keys())


if __name__ == "__main__":
    for k, v in CATEGORIES.items():
        print(f"{k:20s} {v['label']:35s} osm={v['osm_filters']}")
