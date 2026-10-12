"""Flask backend for the Urban Mobility Data Explorer."""
"""API tests against a tiny throw-away database built from database/schema.sql.

The real multi-gigabyte database is never touched: DATABASE_PATH is pointed at a
temp file *before* the backend modules are imported.
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_TEMP_DIR = tempfile.mkdtemp()
_TEST_DB = Path(_TEMP_DIR) / "test.db"
os.environ["DATABASE_PATH"] = str(_TEST_DB)

import pytest  # noqa: E402

from backend import filters as filters_module  # noqa: E402
from backend import db  # noqa: E402
from backend.app import WARM_UP_PATHS, create_app, warm_up  # noqa: E402
from backend.routes import analytics, trips  # noqa: E402


def _trip(trip_id, pickup, pu, do, distance, fare, payment=1, tip_pct=20.0, hour=8):
    return (trip_id, 1, pickup, pickup, 1, distance, 1, "N", pu, do, payment, fare, 0, 0.5, 2.0, 0, 0.3, 0,
            fare + 3, 10.0, 15.0, fare / distance, tip_pct, hour, 1)


# The analytics endpoints live in backend/routes/analytics.py (Role D). Until that
# module is merged, tests that need it are skipped instead of failing.
needs_analytics = pytest.mark.skipif(
    not hasattr(analytics, "analytics_bp"), reason="analytics module (Role D) not merged yet")


@pytest.fixture(scope="module")
def client():
    conn = sqlite3.connect(_TEST_DB)
    conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("INSERT INTO vendors VALUES (1, 'Test Vendor')")
    conn.execute("INSERT INTO rate_codes VALUES (1, 'Standard rate')")
    conn.executemany("INSERT INTO payment_types VALUES (?, ?)", [(1, "Credit card"), (2, "Cash")])
    conn.executemany("INSERT INTO zones VALUES (?, ?, ?, ?, ?, ?)", [
        (10, "Manhattan", "Midtown", "Yellow Zone", 40.75, -73.98),
        (20, "Queens", "Astoria", "Boro Zone", 40.77, -73.92),
        (264, "Unknown", "Unknown", "Unknown", None, None),
    ])
    conn.executemany("INSERT INTO trips VALUES (" + ",".join("?" * 25) + ")", [
        _trip(1, "2019-01-02 08:10:00", 10, 20, 5.0, 20.0),
        _trip(2, "2019-01-02 08:20:00", 10, 20, 6.0, 24.0),
        _trip(3, "2019-01-03 09:30:00", 20, 10, 2.0, 8.0, payment=2, tip_pct=None, hour=9),
        _trip(4, "2019-01-03 09:40:00", 264, 264, 1.0, 5.0, hour=9),
    ])
    conn.executescript((ROOT / "database" / "rollups.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    with create_app().test_client() as test_client:
        yield test_client


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_trips_pagination_and_total(client):
    body = client.get("/api/trips?page_size=2&page=2&sort=pickup_ts&order=asc").get_json()
    assert body["total"] == 4 and body["page"] == 2 and len(body["data"]) == 2


def test_trips_sorted_by_fare_descending(client):
    fares = [row["fare_amount"] for row in client.get("/api/trips?sort=fare_amount&order=desc").get_json()["data"]]
    assert fares == sorted(fares, reverse=True)


def test_trips_filters_combine(client):
    body = client.get("/api/trips?pu_borough=Manhattan&min_distance=5.5").get_json()
    assert body["total"] == 1 and body["data"][0]["trip_id"] == 2


def test_date_filter_end_is_inclusive(client):
    assert client.get("/api/trips?start=2019-01-03&end=2019-01-03").get_json()["total"] == 2


def test_bad_sort_column_is_rejected(client):
    assert client.get("/api/trips?sort=total_amount;DROP TABLE trips").status_code == 400


def test_bad_number_is_rejected(client):
    assert client.get("/api/trips?min_fare=abc").status_code == 400


def test_trip_detail_and_404(client):
    assert client.get("/api/trips/1").get_json()["data"]["vendor"] == "Test Vendor"
    assert client.get("/api/trips/999").status_code == 404


def test_zones(client):
    assert len(client.get("/api/zones").get_json()["data"]) == 3


@needs_analytics
def test_summary(client):
    data = client.get("/api/analytics/summary").get_json()["data"]
    assert data["trips"] == 4


@needs_analytics
def test_hourly_groups_by_hour(client):
    rows = client.get("/api/analytics/hourly").get_json()["data"]
    assert {row["hour"]: row["trips"] for row in rows} == {8: 2, 9: 2}


@needs_analytics
def test_top_zones_excludes_unknown_and_ranks(client):
    rows = client.get("/api/analytics/top-zones?k=5").get_json()["data"]
    assert [row["location_id"] for row in rows] == [10, 20]
    assert rows[0]["trips"] == 2


@needs_analytics
def test_top_routes_excludes_unknown(client):
    rows = client.get("/api/analytics/top-routes?k=5").get_json()["data"]
    assert (rows[0]["pu_zone_id"], rows[0]["do_zone_id"], rows[0]["trips"]) == (10, 20, 2)
    assert all(row["pu_zone_id"] != 264 for row in rows)


@needs_analytics
def test_invalid_k_is_rejected(client):
    assert client.get("/api/analytics/top-zones?k=0").status_code == 400


# ---- roll-up tables must give exactly the same answers as the raw trips table ----

ROLLUP_VS_RAW_PATHS = [
    "/api/analytics/summary",
    "/api/analytics/hourly?hour_min=8&hour_max=8",
    "/api/analytics/daily?start=2019-01-03&end=2019-01-03",
    "/api/analytics/borough?pu_borough=Manhattan",
    "/api/analytics/payment-types?payment_type_id=1",
    "/api/analytics/zone-counts",
    "/api/analytics/top-zones?k=5&by=dropoff",
    "/api/analytics/top-routes?k=5",
    # distance / fare filters that sit on band edges use the banded roll-ups
    "/api/analytics/summary?min_distance=5",
    "/api/analytics/hourly?max_distance=4.99&min_fare=5",
    "/api/analytics/top-routes?k=5&min_distance=2&max_distance=9.99&max_fare=24.99",
    "/api/analytics/borough?min_fare=10&max_fare=29.99&pu_borough=Manhattan",
    # route questions with payment type and/or a date filter
    "/api/analytics/top-routes?k=5&payment_type_id=1",
    "/api/analytics/top-zones?k=5&by=dropoff&payment_type_id=1&min_distance=2",
    "/api/analytics/top-routes?k=5&start=2019-01-02&end=2019-01-02&pu_borough=Manhattan",
    "/api/analytics/top-routes?k=5&start=2019-01-02&hour_min=8",
]


@needs_analytics
@pytest.mark.parametrize("path", ROLLUP_VS_RAW_PATHS)
def test_rollup_answers_equal_raw_answers(client, monkeypatch, path):
    analytics._CACHE.clear()
    from_rollup = client.get(path).get_json()
    monkeypatch.setattr(filters_module, "rollups_available", lambda: False)
    analytics._CACHE.clear()
    from_raw = client.get(path).get_json()
    assert from_rollup == from_raw


def test_source_selection(client):
    parse = filters_module.parse_filters
    kind = lambda args, fn=filters_module.zone_source: fn(parse(args)).kind  # noqa: E731
    assert kind({}) == "rollup"
    assert kind({"min_distance": "5"}) == "band"
    assert kind({"min_distance": "2.5"}) == "raw"                 # not on a band edge
    assert kind({}, filters_module.route_source) == "rollup"
    assert kind({"start": "2019-01-03"}, filters_module.route_source) == "rollup"  # day-level roll-up
    assert kind({"start": "2019-01-03", "hour_min": "8"}, filters_module.route_source) == "raw"
    assert kind({"payment_type_id": "2"}, filters_module.route_source) == "rollup"
    assert kind({"min_fare": "10"}, filters_module.route_source) == "band"


def test_trip_list_total_matches_for_band_and_raw_filters(client):
    banded = client.get("/api/trips?min_distance=5").get_json()["total"]
    off_edge = client.get("/api/trips?min_distance=4.5").get_json()["total"]
    assert banded == off_edge == 2  # trips of 5.0 and 6.0 miles


def test_trip_list_empty_result_and_page_past_the_end(client):
    empty = client.get("/api/trips?min_fare=400").get_json()
    assert empty["total"] == 0 and empty["data"] == []
    past_end = client.get("/api/trips?page=50").get_json()
    assert past_end["total"] == 4 and past_end["data"] == []


def test_trip_list_same_rows_whichever_index_strategy_is_used(client, monkeypatch):
    path = "/api/trips?pu_borough=Manhattan&min_distance=5&sort=fare_amount&order=desc"
    small_mode = client.get(path).get_json()["data"]
    monkeypatch.setattr(trips, "SMALL_RESULT_ROWS", 0)  # force the "broad filters" strategy
    large_mode = client.get(path).get_json()["data"]
    assert [row["trip_id"] for row in small_mode] == [row["trip_id"] for row in large_mode] == [2, 1]


# ---- time limit and warm-up ----

def test_long_query_is_stopped_with_query_timeout(client, monkeypatch):
    monkeypatch.setattr(db, "QUERY_TIME_LIMIT", 0.05)
    endless = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT COUNT(*) FROM c"
    with pytest.raises(db.QueryTimeout):
        db.query(endless)


def test_time_limit_zero_means_no_limit(client, monkeypatch):
    monkeypatch.setattr(db, "QUERY_TIME_LIMIT", 0)
    assert db.query_one("SELECT COUNT(*) AS n FROM trips")["n"] == 4


def test_timeout_becomes_http_504_with_a_helpful_message(client, monkeypatch):
    def too_slow(*args, **kwargs):
        raise db.QueryTimeout("This combination of filters takes too long to answer.")
    monkeypatch.setattr(trips, "query_one", too_slow)
    trips._COUNT_CACHE.clear()
    response = client.get("/api/trips?min_fare=1")
    assert response.status_code == 504
    assert "too long" in response.get_json()["error"]


@needs_analytics
def test_warm_up_runs_every_opening_request(client):
    analytics._CACHE.clear()
    results = warm_up(create_app())
    assert [path for path, _, _ in results] == WARM_UP_PATHS
    # zones/geojson is a generated file that the tiny test database does not have
    assert all(status == 200 for path, status, _ in results if path != "/api/zones/geojson")
    assert len(analytics._CACHE) >= 9  # answers are now cached for the first visitor


def test_filters_that_select_everything_are_ignored(client):
    parse = filters_module.parse_filters
    everything = parse({"hour_min": "0", "hour_max": "23", "start": "2019-01-01", "end": "2019-01-31"})
    assert all(value is None for value in filters_module.effective_filters(everything).values())
    narrow = parse({"hour_min": "1", "start": "2019-01-03"})
    assert filters_module.effective_filters(narrow)["hour_min"] == 1
    assert filters_module.effective_filters(narrow)["start"] is not None
    # all-day, whole-month routes take the roll-up, not the raw table
    assert filters_module.route_source(everything).kind == "rollup"


@needs_analytics
def test_no_op_filters_give_the_same_answer_as_no_filters(client):
    analytics._CACHE.clear()
    plain = client.get("/api/analytics/top-routes?k=5").get_json()
    padded = client.get("/api/analytics/top-routes?k=5&hour_min=0&hour_max=23&start=2019-01-01&end=2019-01-31").get_json()
    assert plain == padded
