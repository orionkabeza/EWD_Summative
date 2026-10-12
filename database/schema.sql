PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vendors(
    vendor_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_codes (
    rate_code_id INTEGER PRIMARY KEY,
    description  TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS payment_types (
    payment_type_id INTEGER PRIMARY KEY,
    description     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zones (
    location_id INTEGER PRIMARY KEY,
    borough     TEXT NOT NULL,
    zone        TEXT NOT NULL,
    service_zone TEXT NOT NULL,
    centroid_lat REAL,
    centroid_lon REAL
);

    CREATE TABLE IF NOT EXISTS trips (
        trip_id               INTEGER PRIMARY KEY,
        vendor_id             INTEGER NOT NULL REFERENCES vendors(vendor_id),
        pickup_ts             TEXT    NOT NULL,
        dropoff_ts            TEXT    NOT NULL,
        passenger_count       INTEGER NOT NULL CHECK (passenger_count BETWEEN 1 AND 6),
        trip_distance         REAL    NOT NULL CHECK (trip_distance > 0),
        rate_code_id          INTEGER NOT NULL REFERENCES rate_codes(rate_code_id),
        store_and_fwd_flag    TEXT    NOT NULL CHECK (store_and_fwd_flag IN ('Y', 'N')),
        pu_zone_id            INTEGER NOT NULL REFERENCES zones(location_id),
        do_zone_id            INTEGER NOT NULL REFERENCES zones(location_id),
        payment_type_id       INTEGER NOT NULL REFERENCES payment_types(payment_type_id),
        fare_amount           REAL    NOT NULL,
        extra                 REAL    NOT NULL,
        mta_tax               REAL    NOT NULL,
        tip_amount            REAL    NOT NULL,
        tolls_amount          REAL    NOT NULL,
        improvement_surcharge REAL    NOT NULL,
        congestion_surcharge  REAL    NOT NULL,
        total_amount          REAL    NOT NULL,

        trip_duration_min     REAL    NOT NULL CHECK (trip_duration_min > 0),
        avg_speed_mph         REAL,
        fare_per_mile         REAL,
        tip_pct               REAL,
        pickup_hour           INTEGER NOT NULL CHECK (pickup_hour BETWEEN 0 AND 23),
        pickup_dow            INTEGER NOT NULL CHECK (pickup_dow BETWEEN 0 AND 6)
    );
