# VIC Lead Finder — Notes (Phase 1: Discovery only)

## What this is
Phase 1 of a larger business-outreach system. This phase ONLY discovers and
categorizes Victorian businesses by postcode. It does NOT send any email or
SMS, and does NOT capture consent. See the top-level project plan for
Phases 2-6 (consent-gate, email engine, SMS engine, reporting, compliance QA).

## Why OpenStreetMap/Overpass instead of Google Places API
Google's Places API Terms of Service prohibit pre-fetching, caching, or
storing Places content to build an independent database of places outside
of displaying it on a Google Map. Bulk-scraping a postcode's businesses into
a local database for cold outreach purposes violates this ToS and risks the
API key/project being terminated. OpenStreetMap data under ODbL explicitly
permits storage, reuse, and redistribution (with attribution), so it's the
correct base layer for this use case. Google Places can still be used later
for small-scale, on-demand, non-bulk enrichment of a human-reviewed
shortlist if desired (see fetch.py docstring) -- that pattern stays within
normal API usage patterns because it's not building a stored bulk database.

## Why ABS POA shapefile instead of Nominatim bbox
Verified empirically: Nominatim's geocoder returns Australian postcodes as a
bare Point geometry (no real polygon), so its bounding box is a crude
heuristic. For postcode 3121 (Richmond) this produced a bbox 4x too wide in
each dimension, spilling into ~20 neighbouring postcodes (CBD, Carlton,
Fitzroy, Malvern, etc.) -- confirmed via direct DB inspection during Phase 1
testing (942 of 965 initial rows had no confirmed postcode match).

Fix: downloaded the official ABS ASGS Postal Areas (POA) 2021 shapefile
(CC BY 4.0, ~2644 postcode polygons for all of Australia) and use real
point-in-polygon filtering (shapely) against the actual postcode boundary.
This cut postcode 3121's business count from 965 (mostly wrong) to 60
(all geo-confirmed inside the real polygon).

Source: https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/POA_2021_AUST_GDA2020_SHP.zip
Stored at: data/boundaries/POA_2021/

## Data quality caveats
- OSM business coverage is community-maintained, not exhaustive. Expect to
  find fewer businesses per postcode than Google Maps would show. Coverage
  is denser in CBD/inner-suburbs, sparser in regional VIC.
- Phone/email/website fields are frequently missing (~15-35% phone, <10%
  email typically) since OSM contact tagging is optional and inconsistent.
  postcode_source='osm_tag' means the business had an explicit addr:postcode
  tag (higher confidence); 'bbox_estimate' means postcode was inferred from
  the search area but the point itself is polygon-confirmed to be genuinely
  inside that postcode (so still accurate, just not independently tagged).
- Category coverage depends on osm_filters in categories.py — extend that
  table for new business types as needed (check OSM wiki Map Features for
  correct tag names before adding).

## Legal/compliance reminder (applies to ALL later phases)
Every business record in this database has consent_status='not_contacted'
by default. Under the Australian Spam Act 2003, sending any commercial
email/SMS requires prior consent (express or inferred from a genuine
existing relationship) -- there is no scraped-list or B2B exemption. This
discovery database is a prospecting/research tool; it is NOT a licence to
mass-email or mass-SMS these contacts. See Phase 2 in the master plan.

## Usage
    cd src
    source ../venv/bin/activate
    python3 discover.py --list-categories
    python3 discover.py --postcode 3121 --categories electrician,plumber,cafe

Output: data/leads.db (SQLite, cumulative across runs) +
output/<postcode>_<timestamp>.csv (per-run review export).

## Known limitations / next steps for Phase 1 hardening
- Overpass public instances occasionally 500/502 under load; retry logic
  with backoff is in fetch.py but a self-hosted Overpass instance would be
  more reliable for heavy/repeated use (see selfhosted-docker-stacks skill
  if that becomes worthwhile).
- Category list (categories.py) currently has ~18 example categories --
  needs expanding/tailoring to match the actual company's ICP once service
  categories are confirmed (Phase 0 task).
- No email/website scraping for contact enrichment yet — could add a
  lightweight "visit business website, extract contact page email" step for
  shortlisted (human-approved) businesses only.
