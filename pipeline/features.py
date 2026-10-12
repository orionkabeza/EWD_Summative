""" Derived features computed from the cleaned trip columns.

Each feature combines several raw columnns into a metric that answers an urban mobility or economics question the raw data cannot answer directly."""


import numpy as np
import pandas as pd 

FEATURE_COLUMNS = [
    "trip_duration_min", "avg_speed_mph", "fare_per_mile", "tip_pct", "pickup_hour", "pickup_dow",

]

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
CREDIT_CARD_PAYMENT_TYPE = 1


def add_features(clean_df):
    """Return a copy of ``clean_df`` with six derived columns appended.
    
    Expects the database-ready columns produced by ``pipeline.clean(so distance, fare and duration are already known to be positive; the guards below only protect against misuse).
    """

    df = clean_df.copy()
    pickup = pd.to_datetime(df["pickup_ts"], format=TIMESTAMP_FORMAT)
    dropoff = pd.to_datetime(df["dropoff_ts"], format=TIMESTAMP_FORMAT)


    # trip_duration_min = dropoff - pickup, in minutes
    # why: the raw data only has two timestamps. Duration is the basis for speed
    # and shows how long people actually spend in a taxi.
    duration_min = (dropoff -pickup).dt.total_seconds()/ 60.0
    df["trip_duration_min"] = duration_min.round(2)

    # avg_speed_mph = distance / (duration in hours).
    # why: a proxy for congestion. The same route at 8 mph vs 20 mph tells us
    # when and where the city is gridlocked.
    hours = duration_min / 60.0
    df["avg_speed_mph"] = (df["trip_distance"] / hours.where(hours > 0)).round(2)

    # fare_per_mile = metered fare / distance.
    # why: a price-per-distance measure that makes short and long trips
    # comparable and exposes expensive short hops (airport flat fares, tolls,
    # waiting in traffic).
    df["fare_per_mile"] = (df["fare_amount"] / df["trip_distance"].where(df["trip_distance"] > 0)).round(2)

    # tip_pct = tip / fare * 100.0, only for credit-card trips.
    # why: the meter records tips only for card payments; cash tips are stored as
    # 0, which would drag every average down. Non-card trips are left empty
    # (NULL) so averages are not biased.
    tip_pct = df["tip_amount"] / df["fare_amount"].where(df["fare_amount"] > 0) * 100
    df["tip_pct"] = tip_pct.where(df["payment_type_id"] == CREDIT_CARD_PAYMENT_TYPE).round(2)

    # pickup_hour (0-23) and pickup_dow (0=Monday ... 6=Sunday).
    # why: the building blocks for demand-by-hour and weekday-vs-weekend views.
    df["pickup_hour"] = pickup.dt.hour.astype("int64")
    df["pickup_dow"] = pickup.dt.dayofweek.astype("int64")

    return df.replace([np.inf, -np.inf], np.nan)

