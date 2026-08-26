#!/usr/bin/env python3
"""
Build a static HTML page listing Melbourne metro gaming (pokies) venues,
sourced from the official VGCCC "Current Gaming Expenditure by Venue"
dataset (CC BY 4.0), with locations resolved via OSM Nominatim geocoding.

Output: output/melbourne_pokie_venues.html (self-contained, uses Leaflet CDN
+ vanilla JS for search/sort/filter, no build step needed).
"""
import json
from pathlib import Path
from datetime import date

GEOCODED = Path("data/gaming/geocoded.jsonl")
OUT_HTML = Path("output/melbourne_pokie_venues.html")


def load_venues():
    venues = []
    with open(GEOCODED) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            venues.append(json.loads(line))
    return venues


def build_html(venues):
    total_egm = sum(v["egm"] for v in venues if v.get("egm"))
    reliable_geo = sum(1 for v in venues if v.get("geo") and not v.get("low_confidence_match"))
    precise_geo = sum(1 for v in venues if v.get("geo") and not v.get("low_confidence_match") and not v.get("approximate_location"))
    approx_geo = reliable_geo - precise_geo
    lgas = sorted(set(v["lga"] for v in venues))

    # Prepare a clean JS-friendly data array
    js_rows = []
    for v in venues:
        geo = v.get("geo") or {}
        low_conf = bool(v.get("low_confidence_match"))
        usable_geo = bool(geo) and not low_conf
        is_approx = bool(v.get("approximate_location"))
        addr_text = (geo.get("display_name") or "Address not found") if usable_geo else ("Address unverified \u2014 low-confidence geocode match, excluded from map" if low_conf else "Address not found")
        if usable_geo and is_approx:
            addr_text = addr_text + " (map pin is an approximate postcode-area location, not the exact building \u2014 precise geocoding pending)"
        js_rows.append({
            "name": v["name"].title(),
            "lga": v["lga"],
            "type": v["venue_type"],
            "egm": v.get("egm") or 0,
            "lat": geo.get("lat") if usable_geo else None,
            "lon": geo.get("lon") if usable_geo else None,
            "addr": addr_text,
            "geocoded": usable_geo,
            "approx": is_approx,
        })
    js_rows.sort(key=lambda r: (-r["egm"]))
    data_json = json.dumps(js_rows)

    today = date.today().isoformat()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Melbourne Pokie (Gaming Machine) Venues — {today}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root {{
    --bg: #0f1115; --panel: #171a21; --border: #2a2e38; --text: #e6e8eb;
    --muted: #9aa1ab; --accent: #4f9dff; --accent2: #ff6b6b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    background: var(--bg); color: var(--text);
  }}
  header {{
    padding: 24px 28px 12px; border-bottom: 1px solid var(--border);
  }}
  h1 {{ margin: 0 0 6px; font-size: 1.5rem; }}
  .subtitle {{ color: var(--muted); font-size: 0.9rem; line-height: 1.5; max-width: 900px; }}
  .stats {{ display: flex; gap: 18px; margin-top: 14px; flex-wrap: wrap; }}
  .stat {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; }}
  .stat .num {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
  .stat .label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
  .layout {{ display: flex; height: calc(100vh - 168px); min-height: 500px; }}
  .panel {{ display: flex; flex-direction: column; width: 46%; border-right: 1px solid var(--border); }}
  #map {{ flex: 1; }}
  .controls {{ padding: 14px 16px; border-bottom: 1px solid var(--border); display: flex; gap: 10px; flex-wrap: wrap; }}
  input[type=text], select {{
    background: var(--panel); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: 6px; font-size: 0.9rem;
  }}
  input[type=text] {{ flex: 1; min-width: 160px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  thead th {{
    position: sticky; top: 0; background: var(--panel); text-align: left; padding: 8px 10px;
    border-bottom: 1px solid var(--border); cursor: pointer; color: var(--muted);
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em;
  }}
  thead th:hover {{ color: var(--text); }}
  tbody td {{ padding: 8px 10px; border-bottom: 1px solid #1d2028; vertical-align: top; }}
  tbody tr:hover {{ background: #1a1e27; cursor: pointer; }}
  tbody tr.selected {{ background: #1e2a3d; }}
  .venue-name {{ font-weight: 600; }}
  .addr {{ color: var(--muted); font-size: 0.78rem; }}
  .egm-badge {{
    display: inline-block; background: var(--accent2); color: #1a1a1a; font-weight: 700;
    padding: 2px 8px; border-radius: 12px; font-size: 0.78rem;
  }}
  .type-badge {{
    display: inline-block; border: 1px solid var(--border); padding: 1px 7px; border-radius: 10px;
    font-size: 0.72rem; color: var(--muted);
  }}
  .table-wrap {{ overflow-y: auto; flex: 1; }}
  footer {{ padding: 14px 28px; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.78rem; line-height: 1.6; }}
  a {{ color: var(--accent); }}
  .no-geo {{ opacity: 0.55; }}
  .leaflet-popup-content-wrapper {{ background: #171a21; color: var(--text); }}
  .leaflet-popup-tip {{ background: #171a21; }}
</style>
</head>
<body>

<header>
  <h1>&#127920; Melbourne Metro Pokie (Gaming Machine) Venues</h1>
  <div class="subtitle">
    Every hotel and club in metropolitan Melbourne currently licensed to operate Electronic
    Gaming Machines (EGMs / "pokies"), sourced from the Victorian Gambling and Casino Control
    Commission's official published dataset. Click a row to locate it on the map.
  </div>
  <div class="stats">
    <div class="stat"><div class="num">{len(venues)}</div><div class="label">Licensed venues</div></div>
    <div class="stat"><div class="num">{total_egm:,}</div><div class="label">Total EGMs</div></div>
    <div class="stat"><div class="num">{len(lgas)}</div><div class="label">Council areas (LGAs)</div></div>
    <div class="stat"><div class="num">{reliable_geo}/{len(venues)}</div><div class="label">Locations mapped ({approx_geo} approx.)</div></div>
  </div>
</header>

<div class="layout">
  <div class="panel">
    <div class="controls">
      <input type="text" id="search" placeholder="Search venue name, suburb, LGA...">
      <select id="lgaFilter"><option value="">All LGAs</option></select>
      <select id="typeFilter">
        <option value="">All types</option>
        <option value="Hotel">Hotel</option>
        <option value="Club">Club</option>
      </select>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th data-sort="name">Venue</th>
            <th data-sort="type">Type</th>
            <th data-sort="egm" style="text-align:right">EGMs</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>
  <div id="map"></div>
</div>

<footer>
  Data source: Victorian Gambling and Casino Control Commission (VGCCC), "Current Gaming
  Expenditure by Venue" dataset (Semi-Annual EGM Venue Level Expenditure, Jul 2025 &ndash; Jun 2026
  release), licensed under
  <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a>.
  EGM counts are the average number of operating machines reported for June 2026 and are updated
  by the regulator semi-annually. That dataset lists venue name and council area only, not street
  addresses, so addresses/coordinates were separately researched via web search and OpenStreetMap
  Nominatim geocoding, then cross-checked with a name/address plausibility filter to catch
  mismatches. Solid-filled markers are precisely geocoded to the venue's street address. Faded,
  dashed-outline markers show a real, verified street address in the popup/table but are pinned at
  their postcode area's centroid rather than the exact building, because precise geocoding for
  that address is still pending (typically due to third-party geocoder rate limits) &ndash; treat
  the address text as authoritative and the pin position as approximate only for those. Rows
  marked "Address not found" or "unverified" have no confirmed location at all and are excluded
  from the map entirely rather than risk showing an incorrect one. This directory reflects
  licensed gaming machine venues only (hotels/clubs) and does not include Crown Casino, Keno-only,
  or wagering-only outlets. Compiled {today}.
</footer>

<script>
const venues = {data_json};

const tbody = document.getElementById('tbody');
const searchInput = document.getElementById('search');
const lgaFilter = document.getElementById('lgaFilter');
const typeFilter = document.getElementById('typeFilter');

// populate LGA filter
const lgas = [...new Set(venues.map(v => v.lga))].sort();
for (const l of lgas) {{
  const opt = document.createElement('option');
  opt.value = l; opt.textContent = l;
  lgaFilter.appendChild(opt);
}}

const map = L.map('map').setView([-37.85, 145.0], 10);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '&copy; OpenStreetMap contributors',
  maxZoom: 18,
}}).addTo(map);

const markers = {{}};
let currentSort = {{ key: 'egm', dir: -1 }};
let selectedRow = null;

function egmColor(egm) {{
  if (egm >= 80) return '#ff4d4d';
  if (egm >= 40) return '#ffa64d';
  return '#4f9dff';
}}

function render() {{
  const q = searchInput.value.toLowerCase();
  const lga = lgaFilter.value;
  const type = typeFilter.value;

  let filtered = venues.filter(v => {{
    if (lga && v.lga !== lga) return false;
    if (type && v.type !== type) return false;
    if (q && !(v.name.toLowerCase().includes(q) || v.lga.toLowerCase().includes(q) || v.addr.toLowerCase().includes(q))) return false;
    return true;
  }});

  filtered.sort((a, b) => {{
    const k = currentSort.key;
    if (a[k] < b[k]) return -1 * currentSort.dir;
    if (a[k] > b[k]) return 1 * currentSort.dir;
    return 0;
  }});

  tbody.innerHTML = '';
  map.eachLayer(l => {{ if (l instanceof L.Marker) map.removeLayer(l); }});

  const bounds = [];
  filtered.forEach((v, idx) => {{
    const tr = document.createElement('tr');
    if (!v.geocoded) tr.classList.add('no-geo');
    tr.innerHTML = `
      <td>
        <div class="venue-name">${{v.name}}</div>
        <div class="addr">${{v.addr}}</div>
        <div class="addr" style="opacity:0.7">${{v.lga}}</div>
      </td>
      <td><span class="type-badge">${{v.type}}</span></td>
      <td style="text-align:right"><span class="egm-badge">${{v.egm}}</span></td>
    `;
    tr.addEventListener('click', () => {{
      if (selectedRow) selectedRow.classList.remove('selected');
      tr.classList.add('selected');
      selectedRow = tr;
      if (v.lat && v.lon) {{
        map.flyTo([v.lat, v.lon], 15);
        if (markers[idx]) markers[idx].openPopup();
      }}
    }});
    tbody.appendChild(tr);

    if (v.lat && v.lon) {{
      const marker = L.circleMarker([v.lat, v.lon], {{
        radius: 6 + Math.min(v.egm / 15, 8),
        color: egmColor(v.egm),
        fillColor: egmColor(v.egm),
        fillOpacity: v.approx ? 0.35 : 0.75,
        weight: v.approx ? 1 : 1,
        dashArray: v.approx ? '3,3' : null,
      }}).addTo(map);
      marker.bindPopup(`<b>${{v.name}}</b><br>${{v.type}} &middot; ${{v.egm}} EGMs<br>${{v.addr}}`);
      markers[idx] = marker;
      bounds.push([v.lat, v.lon]);
    }}
  }});

  if (bounds.length && (q || lga || type)) {{
    map.fitBounds(bounds, {{ padding: [30, 30], maxZoom: 14 }});
  }}
}}

document.querySelectorAll('th[data-sort]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.sort;
    if (currentSort.key === key) currentSort.dir *= -1;
    else {{ currentSort.key = key; currentSort.dir = key === 'egm' ? -1 : 1; }}
    render();
  }});
}});

searchInput.addEventListener('input', render);
lgaFilter.addEventListener('change', render);
typeFilter.addEventListener('change', render);

render();
</script>
</body>
</html>
"""
    return html


def main():
    venues = load_venues()
    html = build_html(venues)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html)
    print(f"Wrote {OUT_HTML} ({len(venues)} venues, {len(html):,} bytes)")


if __name__ == "__main__":
    main()
