CREATE INDEX IF NOT EXISTS idx_trips_pickup_ts     ON trips(pickup_ts);
CREATE INDEX IF NOT EXISTS idx_trips_pu_zone       ON trips(pu_zone_id);
CREATE INDEX IF NOT EXISTS idx_trips_do_zone       ON trips(do_zone_id);
CREATE INDEX IF NOT EXISTS idx_trips_route         ON trips(pu_zone_id, do_zone_id);
CREATE INDEX IF NOT EXISTS idx_trips_distance      ON trips(trip_distance);
CREATE INDEX IF NOT EXISTS idx_trips_fare          ON trips(fare_amount);
CREATE INDEX IF NOT EXISTS idx_trips_hour          ON trips(pickup_hour);
CREATE INDEX IF NOT EXISTS idx_trips_payment       ON trips(payment_type_id);

