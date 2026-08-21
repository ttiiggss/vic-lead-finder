"""SQLite schema + connection helper for the business lead database."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "leads.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_type TEXT NOT NULL,          -- node/way/relation
    osm_id INTEGER NOT NULL,
    name TEXT,
    category_key TEXT,               -- key from categories.py
    category_label TEXT,
    osm_tag TEXT,                    -- the raw matching tag e.g. 'shop=electrical'
    phone TEXT,
    email TEXT,
    website TEXT,
    address TEXT,
    postcode TEXT,
    postcode_source TEXT DEFAULT 'osm_tag',  -- osm_tag | bbox_estimate
    suburb TEXT,
    lat REAL,
    lon REAL,
    source TEXT DEFAULT 'osm',       -- osm | google_enrichment | manual
    consent_status TEXT DEFAULT 'not_contacted',  -- not_contacted|invited|consented|active|unsubscribed
    notes TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(osm_type, osm_id)
);

CREATE INDEX IF NOT EXISTS idx_businesses_postcode ON businesses(postcode);
CREATE INDEX IF NOT EXISTS idx_businesses_category ON businesses(category_key);
CREATE INDEX IF NOT EXISTS idx_businesses_consent ON businesses(consent_status);

CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    postcode TEXT,
    categories TEXT,
    bbox TEXT,
    elements_found INTEGER,
    fetched_at TEXT DEFAULT (datetime('now'))
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


if __name__ == "__main__":
    conn = get_connection()
    print(f"DB initialized at {DB_PATH}")
    conn.close()
