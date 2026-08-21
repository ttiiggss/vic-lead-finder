"""Dedup + storage layer: takes fetched records and upserts them into the DB."""
from db import get_connection


def store_records(conn, records: list[dict]) -> dict:
    """Upsert business records. Returns {'inserted': n, 'updated': n}."""
    inserted = 0
    updated = 0
    cur = conn.cursor()
    for r in records:
        cur.execute(
            "SELECT id FROM businesses WHERE osm_type=? AND osm_id=?",
            (r["osm_type"], r["osm_id"]),
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """UPDATE businesses SET
                    name=?, category_key=?, category_label=?, osm_tag=?,
                    phone=COALESCE(?, phone), email=COALESCE(?, email),
                    website=COALESCE(?, website), address=COALESCE(?, address),
                    postcode=COALESCE(?, postcode), postcode_source=?,
                    suburb=COALESCE(?, suburb), lat=?, lon=?,
                    updated_at=datetime('now')
                   WHERE id=?""",
                (
                    r["name"], r["category_key"], r["category_label"], r.get("osm_tag"),
                    r.get("phone"), r.get("email"), r.get("website"), r.get("address"),
                    r.get("postcode"), r.get("postcode_source", "bbox_estimate"),
                    r.get("suburb"), r.get("lat"), r.get("lon"),
                    existing["id"],
                ),
            )
            updated += 1
        else:
            cur.execute(
                """INSERT INTO businesses
                   (osm_type, osm_id, name, category_key, category_label, osm_tag,
                    phone, email, website, address, postcode, postcode_source,
                    suburb, lat, lon)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    r["osm_type"], r["osm_id"], r["name"], r["category_key"], r["category_label"],
                    r.get("osm_tag"), r.get("phone"), r.get("email"), r.get("website"),
                    r.get("address"), r.get("postcode"), r.get("postcode_source", "bbox_estimate"),
                    r.get("suburb"), r.get("lat"), r.get("lon"),
                ),
            )
            inserted += 1
    conn.commit()
    return {"inserted": inserted, "updated": updated}


def log_fetch(conn, postcode: str, categories: list[str], bbox: dict, elements_found: int):
    conn.execute(
        "INSERT INTO fetch_log (postcode, categories, bbox, elements_found) VALUES (?,?,?,?)",
        (postcode, ",".join(categories), str(bbox), elements_found),
    )
    conn.commit()
