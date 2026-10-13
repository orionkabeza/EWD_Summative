"""Central configuration for the data pipeline

Every cleaning threshold lives here, with one-line justification, so the report can quote them and nobody has to hunt for magic numbers in clean.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
LOGS_DIR = ROOT / "logs"

TRIPS_CSV = RAW_DIR / "yellow_tripdata_2019-01.csv"
ZONE_LOOKUP_CSV = RAW_DIR / "taxi_zone_lookup.csv"
ZONE_SHAPEFILE = RAW_DIR / "taxi_zones" / "taxi_zones.shp"

CLEAN_TRIPS_CSV = PROCESSED_DIR / "trips_clean.csv"
ZONES_CSV = PROCESSED_DIR / "zones.csv"
ZONES_GEOJSON = PROCESSED_DIR / "taxi_zones.geojson"
EXCLUDED_LOG_CSV = LOGS_DIR / "excluded_records.csv"
EXCLUSION_SUMMARY_JSON = LOGS_DIR / "exclusion_summary.json"

CHUNK_SIZE = 250_000  # rows per chunk; keeps memory low for a 656 MB file

# January 2019 extract: a pickup outside it is a bad timestamp.
VALID_PICKUP_START = "2019-01-01 00:00:00"  # inclusive
VALID_PICKUP_END = "2019-02-01 00:00:00"  # exclusive
MAX_TRIP_DISTANCE_MILES = 100.0  # longer is not plausible inside NYC
MAX_DURATION_MIN = 360.0  # over 6 hours is a meter left running
MAX_SPEED_MPH = 100.0  # faster is physically implausible
MAX_FARE_AMOUNT = 500.0  # above this is treated as an error
MIN_PASSENGERS = 1
MAX_PASSENGERS = 6
VALID_RATE_CODES = {1, 2, 3, 4, 5, 6}  # 99 = unknown, excluded
VALID_PAYMENT_TYPES = {1, 2, 3, 4, 5, 6}
DEFAULT_ZONE_IDS = frozenset(range(1, 266))

RAW_TO_CLEAN_COLUMNS = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_ts",
    "tpep_dropoff_datetime": "dropoff_ts",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "RatecodeID": "rate_code_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pu_zone_id",
    "DOLocationID": "do_zone_id",
    "payment_type": "payment_type_id",
    "fare_amount": "fare_amount",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge",
    "congestion_surcharge": "congestion_surcharge",
    "total_amount": "total_amount",
}
CLEAN_COLUMNS = list(RAW_TO_CLEAN_COLUMNS.values())

# Columns that together identify a duplicated trip record.
DEDUP_COLUMNS = [
    "vendor_id", "pickup_dt", "dropoff_dt", "passenger_count", "trip_distance",
    "rate_code_id", "pu_zone_id", "do_zone_id", "payment_type_id",
    "fare_amount", "total_amount",
]
