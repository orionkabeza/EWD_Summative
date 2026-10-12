"""Unit tests for pipeline.clean: one test per cleaning rule."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.clean import DuplicateTracker, clean_chunk  # noqa:E402
from pipeline.config import CLEAN_COLUMNS  # noqa:E402


def make_row(**overides):
    """A valid raw row: tests overide one field to break one rule."""
    row = {
        "source_row": 1,
        "VendorID": 1,
        "tpep_pickup_datetime": "2019-01-05 10:00:00",
        "tpep_dropoff_datetime": "2019-01-05 10:20:00",
        "passenger_count": 1,
        "trip_distance": 3.0,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 161,
        "DOLocationID": 237,
        "payment_type": 1,
        "fare_amount": 14.0,
        "extra": 0.5,
        "mta_tax": 0.5,
        "tips_amount": 17.3,
        "congestion_surcharge": None,
    }
    row.update(overrides)
    return row


def run(*rows):
    raw = pd.DataFrame(list(rows))
    raw["source_row"] = range(1, len(rows) + 1)
    return clean_chunk(raw, tracker=DuplicateTracker())


def assert_excluded_for(code, **overrides):
    clean, excluded = run(make_row())
    assert len(excluded) == 0
    assert list(clean.columns) == CLEAN_COLUMNS
    assert clean.loc[0, "congestion_surcharge"] == 0.0
    assert clean.loc[0, "pickup_ts"] == "2019-01-05 10:00:00"
    assert clean.loc[0, "pu_zone_id"] == 161


def test_missing_value():
    assert_excluded_for("missing_value", fare_amount=None)


def test_unparseable_timestamp_counts_as_missing():
    assert_ecluded_for("missing_value", tpep_pickup_datetime="not a date")


def test_pickup_out_of_range():
    assert_excluded_for("pickup_out_of_range",
                        tpep_pickup_datetime="2008-12-31" 23: 00: 00",
                        tpep_dropoff_datetime="2008-12-31 23: 30:00")
                        

def test_dropoff_not_after_pickup():
    assert_excluded_for("dropoff_not_after_pickup", tpep_dropff_datetime="2019-01-05 09:00:00")

def test_duration_too_long():
    assert_excluded_for("duration_too_long", tpep_dropoff_datetime= "2019-01-06 10:00:00")


def test_distance_non_positive():
    assert_excluded_for("distance_non_positive", trip_distance=0.0)

def test_distance_too_large():
    assert_excluded_for("distance_too_large", trip_distance=500.0)   

def test_implausible_speed():
    assert_excluded_for("implausible_speed", trip_distance=50.0) # 50 miles in 20 min

def test_fare_non_positive():
    assert_excluded_for("fare_non_positive", fare_amount=5.0)

def test_fare_too_large():
    assert_excluded_for("fare_too_large", fare_amount=900.0, total_amount=900.0)


def test_total_non_positive():
    assert_excluded_for("total_non_positive", total_amount=0.0)

def test_negative_charge():
    assert_excluded_for("negative_charge", mta_tax=-0.5)

def test_passenger_count_invalid():
    assert_excluded_for("passenger_count_invalid", passenger_count=0)
    assert_excluded_for("passenger_count_invalid", passenger_count=9)

def test_zone_not_in_lookup():
    assert_excluded_for("pu_zone_not_in_lookup", PULocationID=999)
    assert_excluded_for("do_zone_not_in_lookup", DOLocationID=0)

def test_invalid_rate_code_and_payment_type():
    assert_excluded_for("invalid_rate_code", RatecodeID=99)
    assert_excluded_for("invalid_payment_type", payment_type=9)

def test_duplicate_inside_one_chunk():
    clean, excluded =run(make_row(), make_row())
    assert len(clean) == 1
    assert excluded.loc[0, "reasons"] == "duplicate"

def test_duplicate_across_chunks():
    tracker = DuplicateTracker()
    raw = pd.DataFrame([make_row()])
    first_clean, _ = clean_chunk(raw, tracker=tracker)
    second_clean, second_excluded = clean_chunk(raw, tracker=tracker)
    assert len(first_clean) == 1
    assert len(second_clean) == 0
    assert second_excluded.loc[0,"reasons"] == "duplicate"

def test_several_rules_are_all_listed():
    clean, excluded = run(make_row(trip_distance=0.0, fare_amount=-1.0))
    reasons = excluded.loc[0,"reasons"].split(";")
    assert "distance_non_positive" in reasons and "fare_non_positive" in reasons

def test_unknown_store_flag_becomes_N():
    clean, _ = run(make_row(store_and_fwd_flag=None))
    assert.clean.loc[0, "store_and_fwd_flag"] == "N"



                       