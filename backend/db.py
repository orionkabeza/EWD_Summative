import os
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "database" / "urban_mobility.db"))
GEOJSON_PATH = Path(os.environ.get("ZONES_GEoJSON_PATH", ROOT / "data" / "processed" / "taxi_zones.geojson"))

QUERY_TIME_LIMIT = float(os.environ.get("QUERY_TIME_LIMIT", 15))

_PROGRESS_STEPS = 20_000

class QueryTimeout(Exception):
    pass

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at {DB_PATH}, Run `python database/load_db.py` to create the database first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA cache_size = -200000")
    return conn


def query(sql, params=()):
    conn = get_connection()
    limit = QUERY_TIME_LIMIT
    deadline = time.monotonic() + limit
    if limit > 0:
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, _PROGRESS_STEPS)
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    except sqlite3.OperationalError as error:
        if limit > 0 and time.monotonic() > deadline and "interrupt" in str(error).lower():
           raise QueryTimeout(
               f"This combination of filters takes longer than the {limit:g}-second limit to answer."
               "Try a shorter date range or fewer filters.") from error
        raise
    finally:
        conn.close()



def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None
