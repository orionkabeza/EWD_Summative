import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import DB_PATH


DUMP_PATH = ROOT / "database" / "dump" / "urban_mobility_sample_dump.sql"

def main(rows):
    if not DB_PATH.exists():
        sys.exit(f"{DB_PATH} not found. Run `python database/load_db.py` first.")


    source = sqlite3.connect(DB_PATH)
    sample = sqlite3.connect(":memory:")
    sample.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))

    for table in ("vendors", "rate_codes", "payment_types", "zones"):
        data = source.execute(f"SELECT * FROM {table}").fetchall()
        marks = ",".join("?" * len(data[0]))
        sample.executemany(f"INSERT INTO {table} VALUES({marks})", data)

    trips =  source.execute("SELECT * FROM trips ORDER BY trip_id Limit ?", (rows,)).fetchall()
    sample.executemany(f"INSERT INTO trips VALUES ({','.join('?' * len(trips[0]))})", trips)
    sample.executescript((ROOT / "database" / "indexes.sql").read_text(encoding="utf-8"))
    sample.executescript((ROOT / "database" / "rollups.sql").read_text(encoding="utf-8"))


    DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DUMP_PATH, "w", encoding="utf-8") as handle:
        for line in sample.iterdump():
            handle.write(line + "\n")
    print(f"Wrote {DUMP_PATH} ({len(trips)} trips)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
