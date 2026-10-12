SELECT pickup_hour, COUNT(*) AS trips, ROUND(AVG(avg_speed_mph), 2) AS avg_speed_mph
FROM trips
GROUP BY pickup_hour
ORDER BY pickup_hour;


SELECT z.borough, COUNT(*) AS trips, ROUND(AVG(t.fare_amount), 2) AS avg_fare
FROM trips t
JOIN zones z ON z.location_id = t.pu_zone_id
GROUP BY z.borough
ORDER BY trips DESC;



SELECT pz.zone AS pickup_zone, dz.zone AS dropoff_zone, COUNT(*) AS trips
FROM trips t
JOIN zones pz ON pz.location_id = t.pu_zone_id
JOIN zones dz ON dz.location_id = t.do_zone_id
WHERE t.pu_zone_id NOT IN (264, 265) AND t.do_zone_id NOT IN (264, 265)
GROUP BY t.pu_zone_id, t.do_zone_id
ORDER BY trips DESC
LIMIT 10;


SELECT CASE WHEN trip_distance < 1 THEN '< 1 mi'
            WHEN trip_distance < 3 THEN '1-3 mi'
            WHEN trip_distance < 10 THEN '3-10 mi'
            ELSE '10+ mi' END AS distance_band,
       COUNT(*) AS trips,
       ROUND(AVG(tip_pct), 2) AS avg_tip_pct
FROM trips
WHERE payment_type_id = 1
GROUP BY distance_band;


SELECT z.borough,
       CASE WHEN t.pickup_hour BETWEEN 7 AND 9 THEN 'morning rush'
            WHEN t.pickup_hour BETWEEN 16 AND 19 THEN 'evening rush'
            ELSE 'other' END AS period,
        ROUND(AVG(t.fare_per_mile), 2) AS avg_fare_per_mile
FROM trips t
JOIN zones z ON z.location_id = t.pu_zone_id
WHERE t.trip_distance >= 1
GROUP BY z.borough, period;


SELECT t.trip_id
FROM trips t
LEFT JOIN zones z ON z.location_id = t.pu_zone_id
WHERE z.location_id IS NULL
LIMIT 5;
