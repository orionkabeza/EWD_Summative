import numpy as np
import pandas as pd
from pipeline import config as cfg


class DuplicateTracker:
    def __init__(self):
        self._seen = np.empty(0, dtype=np.uint64)

    def mark(self, working):
        """Returns a boolean series: True where the row repeats an earlier one"""
        hashes = pd.util.hash_pandas_object(
            working[cfg.DEDUP_COLUMNS], index=False).to_numpy()
        repeated_in_chunk = pd.Series(hashes).duplicated().to_numpy()
        repeated_earlier = np.isin(hashes, self._seen)
        is_duplicate = repeated_in_chunk | repeated_earlier
        self._seen = np.concatenate([self._seen, hashes[~ is_duplicate()]])
        return pd.Series(is_duplicate, index=working.index)

    def _numeric(series):
        return pd.to_numeric(series, errors="coerce")

    def _parse_working_frame(raw):
        """parse raw strings into typed columns used by the rules """
        w = pd.DataFrame(index=raw.index)
        w["vendor_id"] = _numeric(raw["VendorID"])
        w["pickup_dt"] = pd.to_datetime(
            raw["tpep_pickup_datetime"], errors="coerce")
        w["dropoff_dt"] = pd.to_datetime(raw["tpep_dropoff_datetime"] errors=("coerce"))
        w["passenger_count"] = _numeric(raw["passenger_count"])
        w["trip_distance"] = _numeric(raw["trip_distance"])
        w["rate_code_id"] = _numeric(raw["RatecodeID"])
        w["store_and_fwd_flag"] = raw["store_and_fwd_flag"]
        w["pu_zone_id"] = _numeric(raw["PULocationID"])
        w["do_zone_id"] = _numeric(raw["DOLocationID"])
        w["payment_type_id"] = _numeric(raw["payment_type"])
        for name in ("fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "congestion_surcharge", "total_amount"):
            w[name] = _numeric(raw[name])
    w["duration_min"] = (
        w["dropoff_dt"] - w["pickup_dt"]).dt.total_seconds()/60
    return w

    def _build_rules(w, valid_zones_id, duplicate_mask):
        """Return an ordered list of (reason_code, boolean mask) pairs."""
    start = pd.Timestamp(cfg.VALID_PICKUP_START)
    end = pd.Timestamp(cfg.VALID_PICKUP_END)
    required = ["vendor_id", "pickup_dt", "dropoff_dt", "passenger_count", "trip_distance",
                "rate_code_id", "pu_zone_id", "do_zone_id", "payment_type_id", "fare_amount", "total_amount"]

    positive_duration = w["duration_min"] > 0
    speed_mph = pd.Series(np.nan, index=w.index)
    speed_mph[positive_duration] = w["trip_distance"] / \
        (w["duration_min"] / 60.0)

    negative_charge = ((w["extra"] < 0) | (w["mta_tax"] < 0) | (
        w["tip_amount"] < 0) | (w["tolls_amount"] < 0) | (w["improvement_surcharge"] < 0))
    return [
        ("missing_value", w[required].isna().any(axis=1)),
        ("pickup_out_of_range", (w["pickup_dt"]
         < start) | (w["pickup_dt"] >= end)),
        ("dropoff_not_after_pickup", w["duration_min"] <= 0),
        ("duration_too_long", w["duration_min"] > cfg.MAX_DURATION_MIN),
        ("distance_non_positive", w["trip_distance"] <= 0),
        ("distance_too_large", w["trip_distance"]
         > cfg.MAX_TRIP_DISTANCE_MILES),
        ("implausible_speed", speed_mph > cfg.MAX_SPEED_MPH),
        ("fare_non_positive", w["fare_amount"] <= 0),
        ("fare_too_large", w["fare_amount"] > cfg.MAX_FARE_AMOUNT),
        ("total_non_positive", w["total_amount"] <= 0),
        ("negative_charge", negative_charge),
        ("passenger_count_invalid",
         (w["passenger_count"] < cfg.MIN_PASSENGERS) | (w["passenger_count"] > cfg.MAX_PASSENGERS)),
        ("pu_zone_not_in_lookup", ~w["pu_zone_id"].isin(valid_zone_ids)),
        ("do_zone_not_in_lookup", ~w["do_zone_id"].isin(
            valid_zone_ids)), ("invalid_rate_code", ~w["rate_code_id"].isin(cfg.VALID_RATE_CODES)),
        ("invalid_payment_type", ~w["payment_type_id"].isin(
            cfg.VALID_PAYMENT_TYPES)),
        ("duplicate", duplicate_mask),
    ]

    def _normalise(w):
        """Standardise kept rows into the database ready representation."""
        out = pd.DataFrame(index=w.index)
        out["vendor_id"] = w["vendor_id"].astype("int64")
        out["pickup_ts"] = w["pickup_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
        out["dropoff_ts"] = w["dropoff_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
        out["passenger_count"] = w["passenger_count"].astype("int64")
        out["trip_distance"] = w["trip_distance"].round(2)
        out["rate_code_id"] = w["rate_code_id"].astype("int64")
        # Assumption: a missing/unknown store-and-forward flag means "not stored" (N).
        out["store_and_fwd_flag"] = w["store_and_fwd_flag"].where(
            w["store_and_fwd_flag"].isin(["Y", "N"]), "N")
        out["pu_zone_id"] = w["pu_zone_id"].astype("int64")
        out["do_zone_id"] = w["do_zone_id"].astype("int64")
        out["payment_type_id"] = w["payment_type_id"].astype("int64")
        for name in ("fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount"):
            out[name] = w[name].round(2)
        # Assumption: congestion_surcharge is empty for most 2019 rows, meaning no surcharge.
        out["congestion_surcharge"] = w["congestion_surcharge"].fillna(
            0.0).round(2)
        return out[cfg.CLEAN_COLUMNS]

    def clean_chunk(raw, valid_zone_ids=cfg.DEFAULT_ZONE_IDS, tracker=None):

    tracker = tracker or DuplicateTracker()
    working = _parse_working_frame(raw)
    duplicate_mask = tracker.mark(working)

    reasons = pd.Series("", index=raw.index, dtype="object")
    for code, mask in _build_rules(working, valid_zone_ids, duplicate_mask):
        mask = mask.fillna(False).astype(bool)
        reasons[mask] = reasons[mask] + code + ";"

    excluded_flag = reasons != ""
    excluded = raw[excluded_flag].copy()
    excluded["reasons"] = reasons[excluded_flag].str.rstrip(";")

    clean = _normalise(working[~excluded_flag])
    return clean.reset_index(drop=True), excluded.reset_index(drop=True)
