import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import DB_PATH  # noqa: E402

SCHEMA_SQL = ROOT / "database" / "schema.sql"
INDEXES_SQL = ROOT / "database" / "indexes.sql"
ROLLUPS_SQL = ROOT / "database" / "rollups.sql"
ZONES_CSV = ROOT / "data" / "processed" / "zones.csv"
TRIPS_CSV = ROOT / "data" / "processed" / "trips_clean.csv"
CHUNK_ROWS = 100_000

# Descriptions from the TLC Yellow Trip Data Dictionary.
RATE_CODES = {
    1: "Standard rate", 2: "JFK", 3: "Newark", 4: "Nassau or Westchester",
    5: "Negotiated fare", 6: "Group ride",
}
PAYMENT_TYPES = {
    1: "Credit card", 2: "Cash", 3: "No charge", 4: "Dispute", 5: "Unknown", 6: "Voided trip",
}
# Vendors 1 and 2 are documented by the TLC; any other id found in the data
# (e.g. 4 appears in the January 2019 file) is loaded as "Vendor <id>".
KNOWN_VENDORS = {1: "Creative Mobile Technologies, LLC", 2: "VeriFone Inc."}

TRIP_COLUMNS = [
    "vendor_id", "pickup_ts", "dropoff_ts", "passenger_count", "trip_distance",
    "rate_code_id", "store_and_fwd_flag", "pu_zone_id", "do_zone_id", "payment_type_id",
    "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "congestion_surcharge", "total_amount",
    "trip_duration_min", "avg_speed_mph", "fare_per_mile", "tip_pct",
    "pickup_hour", "pickup_dow",
]


def _rows(frame):
    """DataFrame -> list of tuples with NaN converted to None (SQL NULL)."""
    return frame.astype(object).where(frame.notna(), None).itertuples(index=False, name=None)


def create_schema(conn):
    conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))


def load_lookups(conn, vendor_ids):
    conn.executemany("INSERT INTO rate_codes VALUES (?, ?)", RATE_CODES.items())
    conn.executemany("INSERT INTO payment_types VALUES (?, ?)", PAYMENT_TYPES.items())
    conn.executemany(
        "INSERT INTO vendors VALUES (?, ?)",
        [(int(v), KNOWN_VENDORS.get(int(v), f"Vendor {int(v)}")) for v in sorted(vendor_ids)],
    )
    zones = pd.read_csv(ZONES_CSV)
    conn.executemany("INSERT INTO zones VALUES (?, ?, ?, ?, ?, ?)", _rows(zones))


def load_trips(conn):
    insert_sql = f"INSERT INTO trips ({', '.join(TRIP_COLUMNS)}) VALUES ({', '.join('?' * len(TRIP_COLUMNS))})"
    loaded = 0
    for chunk in pd.read_csv(TRIPS_CSV, chunksize=CHUNK_ROWS):
        conn.executemany(insert_sql, _rows(chunk[TRIP_COLUMNS]))
        loaded += len(chunk)
        print(f"      loaded {loaded:,} trips")
    return loaded


def main():
    started = time.time()
    for needed in (ZONES_CSV, TRIPS_CSV):
        if not needed.exists():
            sys.exit(f"Missing {needed}. Run `python pipeline/run_pipeline.py` first.")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    # Speed over crash-safety during the one-off bulk load; the DB is rebuilt if it fails.
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")

    print("[1/5] Creating schema ...")
    create_schema(conn)

    print("[2/5] Loading lookup tables ...")
    vendor_ids = pd.read_csv(TRIPS_CSV, usecols=["vendor_id"])["vendor_id"].unique()
    load_lookups(conn, vendor_ids)
    conn.commit()

    print("[3/5] Loading trips ...")
    total = load_trips(conn)
    conn.commit()

    print("[4/5] Building indexes ...")
    conn.executescript(INDEXES_SQL.read_text(encoding="utf-8"))

    print("[5/5] Building roll-up tables and analysing ...")
    conn.executescript(ROLLUPS_SQL.read_text(encoding="utf-8"))
    conn.execute("ANALYZE")
    conn.commit()

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()
    print(f"Done in {time.time() - started:.0f}s: {total:,} trips -> {DB_PATH}")
    print(f"Foreign key violations: {len(violations)}")


if __name__ == "__main__":
    main()
