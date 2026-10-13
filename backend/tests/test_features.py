"""Unit tests for pipeline.features.add_features."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.features import FEATURE_COLUMNS, add_features  # noqa: E402


def make_trip(**overrides):
    trip = {
        "pickup_ts": "2019-01-05 10:00:00",  # a Saturday
        "dropoff_ts": "2019-01-05 10:30:00", # 30 minutes later
        "trip_distance": 6.0,
        "fare_amount": 20.0,
        "tip_amount": 4.0,
        "payment_type_id": 1,
    }
    trip.update(overrides)
    return trip


def features_for(**overrides):
    return add_features(pd.DataFrame([make_trip(**overrides)])).iloc[0]


def test_adds_all_feature_columns():
    result = add_features(pd.DataFrame([make_trip()]))
    assert all(column in result.columns for column in FEATURE_COLUMNS)


def test_duration_in_minutes():
    assert features_for().trip_duration_min == 30.0


def test_average_speed_mph():
    assert features_for().avg_speed_mph == 12.0 # 6 miles in half an hour


def test_fare_per_mile():
    assert features_for().fare_per_mile == round(20.0 / 6.0, 2)


def test_tip_percentage_for_card_payment():
    assert features_for().tip_pct == 20.0


def test_tip_percentage_is_empty_for_cash():
    assert math.isnan(features_for(payment_type_id=2, tip_amount=0.0).tip_pct)


def test_hour_and_day_of_week():
    row = features_for()
    assert row.pickup_hour == 10
    assert row.pickup_dow == 5 # saturday (Monday = o)


def test_zero_distance_does_not_crash_or_give_infinity():
    row = features_for(trip_distance=0.0)
    assert math.isnan(row.fare_per_mile)
    assert row.avg_speed_mph == 0.0


def test_input_frame_is_not_modified():
    original = pd.DataFrame([make_trip()])
    add_features(original)
    assert "trip_duration_min" not in original.columns

     
        