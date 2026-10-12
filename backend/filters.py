from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

from backend.db import query


DISTANCE_EDGES = (1, 2, 3, 5, 10, 20)
FARE_EDGES = (5, 10, 15, 20, 30, 50)
MAX_VALUE_OFFSET = 0.01

PICKUP_ZONE_JOIN = "CROSS JOIN zones pz ON pz.location_id = t.pu_zone_id"


RAW_METRICS = {
    "trips": "COUNT(*)",
    "avg_fare": "ROUND(AVG(t.fare_amount), 2)",
    "avg_distance": "ROUND(AVG(t.trip_distance), 2)",
    "avg_duration_min": "ROUND(AVG(t.trip_duration_min), 2)",
    "avg_speed_mph": "ROUND(AVG(t.avg_speed_mph), 2)",
    "avg_tip_pct": "ROUND(AVG(T.tip_pct), 2)",
    "total_revenue": "ROUND(SUM(t.total_amount), 2)",
}
ZONE_ROLLUP_METRICS = {
    "trips": "SUM(t.trips)",
    "avg_fare": "ROUND(SUM(t.sum_fare) / SUM(t.trips), 2)",
    "avg_distance": "ROUND(SUM(t.sum_distance) / SUM(t.trips), 2)",
    "avg_duration_min": "ROUND(SUM(t.sum_duration) / SUM(t.trips), 2)",
    "avg_speed_mph": "ROUND(SUM(t.sum_speed) / SUM(t.speed_trips), 2)",
    "avg_tip_pct": "ROUND(SUM(t.sum_tip_pct) / SUM(t.tip_trips), 2)",
    "total_revenue": "ROUND(SUM(t.sum_total), 2)",
}
ROUTE_ROLLUP_METRICS = {
    "trips": "SUM(t.trips)",
    "avg_fare": "ROUND(SUM(t.sum_fare) / SUM(t.trips), 2)",
}

class FilterError(ValueError):
    pass
def _number(args, name, cast):
    raw = args.get(name)
    if raw in (None, ""):
        return None
    try:
        return cast(raw)
    except ValueError:
        raise FilterError(f"'{name}' must be a number, got '{raw}'")

def _day(args, name):
    raw = args.get(name)
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise FilterError(f"'{name}' must be a date like 2019-01-31, got '{raw}'")

def parse_filters(args):
    filters = {
        "start": _day(args, "start"),
        "end": _day(args, "end"),
        "hour_min": _number(args, "hour_min", int),
        "hour_max": _number(args, "hour_max", int),
        "min_distance": _number(args, "min_distance", float),
        "max_distance": _number(args, "max_distance", float),
        "min_fare": _number(args, "min_fare", float),
        "max_fare": _number(args, "max_fare", float),
        "pu_borough": (args.get("pu_borough") or None),
        "payment_type_id": _number(args, "payment_type_id", int),
    }
    for name in ("hour_min", "hour_max"):
        if filters[name] is not None and not 0 <= filters[name] <= 23:
            raise FilterError(f"'{name}' must be between 0 and 23")
    return filters

def needs_pickup_zone(filters):
    return filters["pu_borough"] is not None


def _has(filters, *names):
    return any(filters[name] is not None for name in names)

def _has_distance_or_fare(filters):
    return _has(filters, "min_distance", "max_distance", "min_fare", "max_fare")


def _band_range(low_value, high_value, edges):


    last_band = len(edges)
    low_band, high_band = 0, last_band
    if low_value is not None and low_value > 0:
        if low_value not in edges:
            return None
        low_band = edges.index(low_value) + 1
    if high_value is not None:
        match = [i for i, edge in enumerate(edges) if abs(high_value - (edge - MAX_VALUE_OFFSET)) < 1e-9]
        if not match:
            return None
        high_band = match[0]
    return low_band, high_band

def _band_ranges(filters):
    distance = _band_range(filters["min_distance"], filters["max_distance"], DISTANCE_EDGES)
    fare = _band_range(filters["min_fare"], filters["max_fare"], FARE_EDGES)
    if distance is None or fare is None:
        return None
    return distance, fare



COLUMN_GROUP = {
    "pickup_ts": "date", "pickup_hour": "hour", "trip_distance": "distance",
    "fare_amount": "fare", "pu_zone_id": "borough", "payment_type_id": "payment",   
}
FILTER_GROUPS = {
    "date": ("start", "end"),
    "hour": ("hour_min", "hour_max"),
    "distance": ("min_distance", "max_distance"),
    "fare": ("min_fare", "max_fare"),
    "borough": ("pu_borough",),
    "payment": ("payment_type_id",),
}

def active_groups(filters):
    return[group for group, names in FILTER_GROUPS.items() if _has(filters, *names)]


def solo_filters(filters, group):
    solo = {name: None for name in filters}
    for name in FILTER_GROUPS[group]:
        solo[name] = filters[name]
    return solo


def _build_where(filters, mode, borough_subquery=False, suppress_groups=frozenset(), sort_column=None):


    conditions, params = [], []

    def plus_for(column):
        return "+" if COLUMN_GROUP[column] in suppress_groups and column != sort_column else ""

    def add(condition, *values):
        conditions.append(condition)
        params.extend(values)

    if mode == "raw":
        if filters["start"]:
            add(f"{plus_for('pickup_ts')}t.pickup_ts >= ?", filters["start"].isoformat())
        if filters ["end"]:

            add(f"{plus_for('pickup_ts')}t.pickup_ts < ?", (filters["end"] + timedelta(days=1)).isoformat())
    else:
        if filters["start"]:
            add("t.pickup_date >= ?", filters["start"].isoformat())
        if filters["end"]:
            add("t.pickup_date <= ?", filters["end"].isoformat())

    if filters["hour_min"] is not None:
        add(f"{plus_for('pickup_hour')}t.pickup_hour >= ?", filters["hour_min"])
    if filters["hour_max"] is not None:
        add(f"{plus_for('pickup_hour')}t.pickup_hour <= ?", filters["hour_max"])

    if mode == "raw":
        if filters["min_distance"] is not None:
            add(f"{plus_for('trip_distance')}t.trip_distance >= ?", filters["min_distance"])
        if filters["max_distance"] is not None:
            add(f"{plus_for('trip_distance')}t.trip_distance <= ?", filters["max_distance"])
        if filters["min_fare"] is not None:
            add(f"{plus_for('fare_amount')}t.fare_amount >= ?", filters["min_fare"])
        if filters["max_fare"] is not None:
            add(f"{plus_for('fare_amount')}t.fare_amount <= ?", filters["max_fare"])      
    elif mode == "band" and _has_distance_or_fare(filters):
        (d_low, d_high), (f_low, f_high) = _band_ranges(filters)
        if (d_low, d_high) !=(0, len(DISTANCE_EDGES)):
            add("t.dist_band BETWEEN ? AND ?", d_low, d_high)
        if (f_low, f_high) !=(0, len(FARE_EDGES)):
            add("t.fare_band BETWEEN ? AND ?", f_low, f_high)

    if filters["pu_borough"]:
        if borough_subquery:
            add(f"{plus_for('pu_zone_id')}t.pu_zone_id IN (SELECT location_id FROM zones WHERE borough = ?)", filters["pu_borough"])
        else:
            add("pz.borough = ?", filters["pu_borough"])
    if filters["payment_type_id"] is not None:
        add(f"{plus_for('payment_type_id')}t.payment_type_id = ?", filters["payment_type_id"])

    return (" WHERE " + " AND ".join(conditions)) if conditions else "", params

def where_clause(filters, suppress_groups=frozenset(), sort_column=None):
    return _build_where(filters, "raw", borough_subquery=True,
                        suppress_groups=suppress_groups, sort_column=sort_column)

@lru_cache(maxsize=1)
def rollups_available():
    names = {row["name"] for row in query(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'agg_%'")}
    return {"agg_zone_hour", "agg_route_hour", "agg_zone_hour_band", "agg_route_hour_band", "agg_route_day"} <= names



DATE_INDEX_MAX_SHARE = 0.2

@lru_cache(maxsize=1)
def data_date_range():
    row = query("SELECT MIN(pickup_date) AS first, MAX(pickup_date) AS last FROM agg_zone_hour")[0]
    return date.fromisoformat(row["first"]), date.fromisoformat(row["last"])


@lru_cache(maxsize=256)
def _date_share(start, end):
    conditions, params = [], []
    if start:
        conditions.append("pickup_date >= ?")
        params.append(start.isoformat())
    if end:
        conditions.append("pickup_date <= ?")
        params.append(end.isoformat())
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    part = query(f"SELECT COALESCE(SUM(trips), 0) AS n FROM agg_zone_hour {where}", params)[0]["n"]
    total = query("SELECT SUM(trips) AS n FROM agg_zone_hour")[0]["n"]
    return part / total if total else 1.0


def effective_filters(filters):


    result = dict(filters)
    if result["hour_min"] == 0:
        result["hour_min"] = None
    if result["hour_max"] == 23:
        result["hour_max"] = None
    if rollups_available() and (result["start"] or result["end"]):
        first, last = data_date_range()
        if result["start"] and result["start"] <= first:
            result["start"] = None
        if result["end"] and result["end"] >= last:
            result["end"] = None
    return result


def _date_index_helps(filters):
    if not _has(filters, "start", "end"):
        return False
    if not rollups_available():
        return True
    return _date_share(filters["start"], filters["end"]) <= DATE_INDEX_MAX_SHARE


@dataclass
class Source:
    from_sql: str
    where: str
    params: list
    metrics: dict
    date_expr: str
    kind: str


    def with_conditions(self, *conditions):
        if not conditions:
            return self.where
        joined = " AND ".join(conditions)
        return f"{self.where} AND {joined}" if self.where else f"WHERE {joined}"

def _make_source(filters, need_pickup_zone, kind, table, metrics, date_expr):
    where, params = _build_where(filters, kind)
    join = PICKUP_ZONE_JOIN if (need_pickup_zone or needs_pickup_zone(filters)) else ""
    if kind == "raw" and (_has_distance_or_fare(filters) or not _date_index_helps(filters)):

        table = f"{table} NOT INDEXED"
    return Source(
        from_sql=f"{table} {join}".strip(),
        where=where,
        params=params,
        metrics=metrics,
        date_expr=date_expr,
        kind=kind,
    
    )

def zone_source(filters, need_pickup_zone=False):

    filters = effective_filters(filters)
    if rollups_available():
        if not _has_distance_or_fare(filters):
            return _make_source(filters, need_pickup_zone, "rollup", "agg_zone_hour t",
                                ZONE_ROLLUP_METRICS, "t.pickup_date")
        if _band_ranges(filters) is not None:
            return _make_source(filters, need_pickup_zone, "band", "agg_zone_hour_band t",
                                ZONE_ROLLUP_METRICS, "t.pickup_date")
    return _make_source(filters, need_pickup_zone, "raw", "trips t",
                        RAW_METRICS, "SUBSTR(t.pickup_ts, 1, 10)")

def route_source(filters, need_pickup_zone=False):

    filters = effective_filters(filters)
    if rollups_available():
        if not _has(filters, "start", "end"):
            if not _has_distance_or_fare(filters):
                return _make_source(filters, need_pickup_zone, "rollup", "agg_route_hour t", ROUTE_ROLLUP_METRICS, "")
            if _band_ranges(filters) is not None:
                return _make_source(filters, need_pickup_zone, "band", "agg_route_hour_band t",
                                    ROUTE_ROLLUP_METRICS, "")
        elif not _has(filters, "hour_min", "hour_max") and not _has_distance_or_fare(filters):
            return _make_source(filters, need_pickup_zone, "rollup", "agg_route_day t",
                                    ROUTE_ROLLUP_METRICS, "t.pickup_date")
    return _make_source(filters, need_pickup_zone, "raw", "trips t", RAW_METRICS, "")
