"""Unit tests for the pure parts of backend.filters (no database needed)."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import filters as f  # noqa: E402


def parse(**args):
    return f.parse_filters({key: str(value) for key, value in args.items()})


def test_empty_query_has_no_filters():
    parsed = parse()
    assert all(value is None for value in parsed.values())
    assert f.active_groups(parsed) == []


def test_values_are_parsed_to_the_right_types():
    parsed = parse(start="2019-01-05", hour_min=6, min_distance="2.5", pu_borough="Queens")
    assert parsed["start"] == date(2019, 1, 5)
    assert parsed["hour_min"] == 6 and parsed["min_distance"] == 2.5
    assert f.active_groups(parsed) == ["date", "hour", "distance", "borough"]


@pytest.mark.parametrize("args", [{"start": "05/01/2019"}, {"hour_min": 24}, {"min_fare": "abc"}, {"hour_max": -1}])
def test_invalid_values_raise_filter_error(args):
    with pytest.raises(f.FilterError):
        parse(**args)


def test_band_range_on_edges():
    edges = f.DISTANCE_EDGES  # (1, 2, 3, 5, 10, 20)
    assert f._band_range(None, None, edges) == (0, 6)       # no filter: every band
    assert f._band_range(5, None, edges) == (4, 6)           # 5 mi or more
    assert f._band_range(None, 4.99, edges) == (0, 3)        # under 5 mi
    assert f._band_range(5, 9.99, edges) == (4, 4)           # exactly the 5-10 mi band
    assert f._band_range(0, None, edges) == (0, 6)           # a minimum of 0 means no filter


def test_band_range_rejects_values_off_the_edges():
    edges = f.DISTANCE_EDGES
    assert f._band_range(2.5, None, edges) is None
    assert f._band_range(None, 5, edges) is None             # "max 5" includes 5.00, which is in the next band
    assert f._band_range(None, 4.5, edges) is None


def test_where_clause_uses_bound_parameters_only():
    sql, params = f.where_clause(parse(pu_borough="x'; DROP TABLE trips;--", min_fare=10))
    assert "DROP" not in sql and "x'" not in sql
    assert "x'; DROP TABLE trips;--" in params


def test_where_clause_end_date_is_inclusive():
    sql, params = f.where_clause(parse(end="2019-01-31"))
    assert "t.pickup_ts < ?" in sql and params == ["2019-02-01"]


def test_suppressed_group_gets_a_leading_plus_except_the_sort_column():
    parsed = parse(min_fare=10, min_distance=5)
    sql, _ = f.where_clause(parsed, suppress_groups={"fare", "distance"}, sort_column="fare_amount")
    assert "+t.trip_distance >= ?" in sql       # suppressed
    assert "+t.fare_amount" not in sql           # sort column stays usable for index seeks
    assert "t.fare_amount >= ?" in sql


def test_solo_filters_keeps_only_one_group():
    parsed = parse(min_fare=10, max_fare=19.99, hour_min=3)
    solo = f.solo_filters(parsed, "fare")
    assert f.active_groups(solo) == ["fare"]
    assert solo["min_fare"] == 10 and solo["hour_min"] is None
