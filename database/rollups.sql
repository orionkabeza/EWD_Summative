DROP TABLE IF EXISTS agg_zone_hour;
CREATE TABLE agg_zone_hour (
    pickup_date     TEXT    NOT NULL,   -- 'YYYY-MM-DD'
    pickup_hour     INTEGER NOT NULL,
    pu_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    payment_type_id INTEGER NOT NULL REFERENCES payment_types(payment_type_id),
    trips           INTEGER NOT NULL,
    sum_fare        REAL    NOT NULL,
    sum_distance    REAL    NOT NULL,
    sum_duration    REAL    NOT NULL,
    sum_speed       REAL    NOT NULL,
    speed_trips     INTEGER NOT NULL,   -- trips with a non-NULL avg_speed_mph
    sum_tip_pct     REAL    NOT NULL,
    tip_trips       INTEGER NOT NULL,   -- trips with a non-NULL tip_pct (card trips)
    sum_total       REAL    NOT NULL,
    PRIMARY KEY (pickup_date, pickup_hour, pu_zone_id, payment_type_id)
) WITHOUT ROWID;

INSERT INTO agg_zone_hour
SELECT SUBSTR(pickup_ts, 1, 10), pickup_hour, pu_zone_id, payment_type_id,
       COUNT(*), SUM(fare_amount), SUM(trip_distance), SUM(trip_duration_min),
       COALESCE(SUM(avg_speed_mph), 0), COUNT(avg_speed_mph),
       COALESCE(SUM(tip_pct), 0), COUNT(tip_pct),
       SUM(total_amount)
FROM trips
GROUP BY 1, 2, 3, 4;

-- Pickup zone -> dropoff zone pairs by pickup hour and payment type
-- (top routes, busiest dropoff zones).
DROP TABLE IF EXISTS agg_route_hour;
CREATE TABLE agg_route_hour (
    pickup_hour     INTEGER NOT NULL,
    pu_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    do_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    payment_type_id INTEGER NOT NULL REFERENCES payment_types(payment_type_id),
    trips           INTEGER NOT NULL,
    sum_fare        REAL    NOT NULL,
    PRIMARY KEY (pickup_hour, pu_zone_id, do_zone_id, payment_type_id)
) WITHOUT ROWID;

INSERT INTO agg_route_hour
SELECT pickup_hour, pu_zone_id, do_zone_id, payment_type_id, COUNT(*), SUM(fare_amount)
FROM trips
GROUP BY 1, 2, 3, 4;

-- The same pairs by pickup DATE and payment type, for route questions with a date
-- filter. Adding the hour as well would make it almost as big as the trips table,
-- so a date filter combined with an hour/distance/fare filter still uses the raw table.
DROP TABLE IF EXISTS agg_route_day;
CREATE TABLE agg_route_day (
    pickup_date     TEXT    NOT NULL,
    pu_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    do_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    payment_type_id INTEGER NOT NULL REFERENCES payment_types(payment_type_id),
    trips           INTEGER NOT NULL,
    sum_fare        REAL    NOT NULL,
    PRIMARY KEY (pickup_date, pu_zone_id, do_zone_id, payment_type_id)
) WITHOUT ROWID;

INSERT INTO agg_route_day
SELECT SUBSTR(pickup_ts, 1, 10), pu_zone_id, do_zone_id, payment_type_id, COUNT(*), SUM(fare_amount)
FROM trips
GROUP BY 1, 2, 3, 4;

DROP TABLE IF EXISTS agg_zone_hour_band;
CREATE TABLE agg_zone_hour_band (
    pickup_date     TEXT    NOT NULL,
    pickup_hour     INTEGER NOT NULL,
    pu_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    payment_type_id INTEGER NOT NULL REFERENCES payment_types(payment_type_id),
    dist_band       INTEGER NOT NULL,
    fare_band       INTEGER NOT NULL,
    trips           INTEGER NOT NULL,
    sum_fare        REAL    NOT NULL,
    sum_distance    REAL    NOT NULL,
    sum_duration    REAL    NOT NULL,
    sum_speed       REAL    NOT NULL,
    speed_trips     INTEGER NOT NULL,
    sum_tip_pct     REAL    NOT NULL,
    tip_trips       INTEGER NOT NULL,
    sum_total       REAL    NOT NULL,
    PRIMARY KEY (pickup_date, pickup_hour, pu_zone_id, payment_type_id, dist_band, fare_band)
) WITHOUT ROWID;

INSERT INTO agg_zone_hour_band
SELECT SUBSTR(pickup_ts, 1, 10), pickup_hour, pu_zone_id, payment_type_id,
       CASE WHEN trip_distance < 1 THEN 0 WHEN trip_distance < 2 THEN 1 WHEN trip_distance < 3 THEN 2
            WHEN trip_distance < 5 THEN 3 WHEN trip_distance < 10 THEN 4 WHEN trip_distance < 20 THEN 5
            ELSE 6 END,
       CASE WHEN fare_amount < 5 THEN 0 WHEN fare_amount < 10 THEN 1 WHEN fare_amount < 15 THEN 2
            WHEN fare_amount < 20 THEN 3 WHEN fare_amount < 30 THEN 4 WHEN fare_amount < 50 THEN 5
            ELSE 6 END,
       COUNT(*), SUM(fare_amount), SUM(trip_distance), SUM(trip_duration_min),
       COALESCE(SUM(avg_speed_mph), 0), COUNT(avg_speed_mph),
       COALESCE(SUM(tip_pct), 0), COUNT(tip_pct),
       SUM(total_amount)
FROM trips
GROUP BY 1, 2, 3, 4, 5, 6;

DROP TABLE IF EXISTS agg_route_hour_band;
CREATE TABLE agg_route_hour_band (
    pickup_hour     INTEGER NOT NULL,
    pu_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    do_zone_id      INTEGER NOT NULL REFERENCES zones(location_id),
    payment_type_id INTEGER NOT NULL REFERENCES payment_types(payment_type_id),
    dist_band       INTEGER NOT NULL,
    fare_band       INTEGER NOT NULL,
    trips           INTEGER NOT NULL,
    sum_fare        REAL    NOT NULL,
    PRIMARY KEY (pickup_hour, pu_zone_id, do_zone_id, payment_type_id, dist_band, fare_band)
) WITHOUT ROWID;

INSERT INTO agg_route_hour_band
SELECT pickup_hour, pu_zone_id, do_zone_id, payment_type_id,
       CASE WHEN trip_distance < 1 THEN 0 WHEN trip_distance < 2 THEN 1 WHEN trip_distance < 3 THEN 2
            WHEN trip_distance < 5 THEN 3 WHEN trip_distance < 10 THEN 4 WHEN trip_distance < 20 THEN 5
            ELSE 6 END,
       CASE WHEN fare_amount < 5 THEN 0 WHEN fare_amount < 10 THEN 1 WHEN fare_amount < 15 THEN 2
            WHEN fare_amount < 20 THEN 3 WHEN fare_amount < 30 THEN 4 WHEN fare_amount < 50 THEN 5
            ELSE 6 END,
       COUNT(*), SUM(fare_amount)
FROM trips
GROUP BY 1, 2, 3, 4, 5, 6;
