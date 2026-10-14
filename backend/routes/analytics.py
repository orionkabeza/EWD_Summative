"""Aggregate endpoints that feed the dashboard charts and map.

All endpoints accept the shared filters from ``backend.filters``, Aggregation is done in SQL (GROUP BY); the ranking endpoints the pass the grouped rows through our hand-written heap (``backend.algorithms.topk``) instead of sorting them.

each query is written once against a ``Source`` (see ``backend.filters``), which is either the raw trips table, whichever can answer the active filters correctly. Both use the alias ``t``.

Responses are ``{"data": ...}``:a list for the chart endpoints, and a single object for ``/summary``."""

from functools import wraps

from flask import Blueprint, jsonify, request

from backend.algorithms.topk import top_k
from backend.db import query, query_one
from backend.filters import FilterError, parse_filters, route_source, zone_source

analytics_bp = Blueprint("analytics", __name__)

DEFAULT_K, MAX_K = 10, 100

#LocationIDs 264 ("Unkown") and 265 ("Outside of NYC") are catch-all buckets, not
#real places, In the data, "unkown -> Unkown" was the single most frequent
#route, which sys nothing about mobility, so rankings exclude them.
UNKNOWN_ZONE_IDS = (264, 265)

_CACHE = {}
_CACHE_LIMIT = 256

def cached(view):
    """Cache a view's JSON per (path, query string).
    
    The dashboard re-asks the same questions often and the database is read-only while the server runs, so a plain in-memory dict is safe; it is bounded so it cannot grow forever.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        key = (request.path, tuple(sorted(request.args.items(multi=True))))
        if key not in _CACHE:
            if len(_CACHE) >= _CACHE_LIMIT:
                _CACHE.clear()
            _CACHE[key] = view(*args, **kwargs)
        return jsonify(_CACHE[key])
    return wrapper

def _known_zones(*columns):
    """Conditions that drop the catch-all zone ids from a ranking."""
    ids = ", ".join(str(i) for i in UNKNOWN_ZONE_IDS)
    return [f"{column} NOT IN ({ids})" for column in columns]

def _parse_k():
    raw = request.args.get("k", str(DEFAULT_K))
    try:
        k = int(raw)
    except ValueError:
        raise FilterError(f"'k' must be an integer, got '{raw}'")
    if not 1 <= k <= MAX_K:
        raise FilterError(f"'k' must be between 1 and {MAX_K}")
    return k

@analytics_bp.route("/summary")
@cached
def summary():
    src = zone_source(parse_filters(request.args))
    m = src.metrics
    row = query_one(f"""
        SELECT {m['trips']} AS trips,
               {m['avg_distance']} AS avg_distance,
               {m['avg_fare']} AS avg_fare,
               {m['avg_duration_min']} AS avg_duration_min,
               {m['avg_speed_mph']} AS avg_speed_mph,
               {m['avg_tip_pct']} AS avg_tip_pct,
               {m['total_revenue']} AS total_revenue
        FROM {src.from_sql} {src.where}
    """, src.params)
    row["trips"] = row["trips"] or 0 # SUM() over zero rows is NULL
    return {"data": row}


@analytics_bp.route("/hourly")
@cached
def hourly():
    src = zone_source(parse_filters(request.args))
    m = src.metrics
    rows = query(f"""
        SELECT t.pickup_hour AS hour,
                {m['trips']} AS trips,
                {m['avg_fare']} AS avg_fare,
                {m['avg_speed_mph']} AS avg_speed_mph
        FROM {src.from_sql} {src.where}
        GROUP BY t.pickup_hour ORDER BY t.pickup_hour
    """, src.params)
    return {"data": rows}

@analytics_bp.route("/daily")
@cached
def daily():
    src = zone_source(parse_filters(request.args))
    m = src.metrics
    rows = query(f"""
        SELECT {src.date_expr} AS date,
               {m['trips']} AS trips,
               {m['avg_fare']} AS avg_fare,
               {m['total_revenue']} AS revenue
        FROM {src.from_sql} {src.where}
        GROUP BY date ORDER BY date
    """, src.params)
    return {"data": rows}

@analytics_bp.route("/borough")
@cached
def borough():
    src = zone_source(parse_filters(request.args), need_pickup_zone=True)
    m = src.metrics
    rows = query(f"""
        SELECT pz.borough AS borough,
               {m['trips']} AS trips,
               {m['avg_fare']} AS avg_fare,
               {m['avg_distance']} AS avg_distance,
               {m['avg_tip_pct']} AS avg_tip_pct
        FROM {src.from_sql} {src.where}
        GROUP BY pz.borough 
        """, src.params)
    ranked = top_k(rows, len(rows), key=lambda r: (r["trips"], r["borough"]))
    return {"data": ranked}


@analytics_bp.route("/payment-types")
@cached
def payment_types():
    src = zone_source(parse_filters(request.args))
    m = src.metrics
    rows = query(f"""
        SELECT t.payment_type_id AS payment_type_id,
                pt.description AS description,
                {m['trips']} AS trips,
                {m['avg_fare']} AS avg_fare,
                {m['avg_tip_pct']} AS avg_tip_pct
        FROM {src.from_sql}
        JOIN payment_types pt ON pt.pt.payment_type_id = t.payment_type_id
        {src.where}
        GROUP BY t.payment_types_id, pt.description
    """, src.params)
    ranked = top_k(rows, len(rows), key=lambda r: (r["trips"], -r["payment_type_id"]))
    return {"data": ranked}



@analytics_bp.route("/zone-counts")
@cached
def zone_counts():
    """Pickups per zone for *all* zones (clours the choropleth map)."""
    src = zone_source(parse_filters(request.args), need_pickup_zone=True)
    m = src.metrics
    rows = query(f"""
        SELECT pz.location_id AS location_id,
               pz.zone AS zone,
               pz.borough AS borough,
               {m['trips']} AS trips,
               {m['avg_fare']} AS avg_fare
        FROM {src.from_sql} {src.where}
        GROUP BY pz.location_id, pz.zone, pz.borough
        """, src.params)
    return {"data": rows}


@analytics_bp.route("/top-zones")
@cached
def top_zones():
    """TOP K busiest zones by pickups(``by=pickup``, default) or dropoffs."""
    filters = parse_filters(request.args)
    k = _parse_k()
    by = request.args.get("by", "pickup")
    if by not in ("pickup", "dropoff"):
        raise FilterError("'by' must be 'pickup' or 'dropoff'")

    if by == "pickup":
        src = zone_source(filters, need_pickup_zone=True)
        where = src.with_conditions(*_known_zones("t.pu_zone_id"))
        sql = f"""
            SELECT pz.location_id AS location_id, pz.zone AS zone, pz.borough AS borough,
                   {src.metrics['trips']} AS trips
            FROM {src.from_sql} {where}
            GROUP BY pz.location_id, pz.zone, pz.borough
            """
    else:
        src = route_source(filters)
        where = src.with_conditions(*_known_zones("t.do_zone_id"))
        sql = f""" 
            SELECT dz.location_id AS location_id, dz.zone AS zone, dz.borough AS borough,
                    {src.metrics['trips']} AS trips
            FROM {src.from_sql}
            JOIN zones dz ON dz.location_id = t.do_zone_id {where}
            GROUP BY dz.location_id, dz.zone, dz.borough"""
    rows = query(sql, src.params)
    # most trips first; equal counts: lower location_id first
    return {"data": top_k(rows, k, key=lambda r: (r["trips"], -r["location_id"]))}


@analytics_bp.route("/top-routes")
@cached
def top_routes():
    """Top K most frequent pickup-zone -> dropoff-zone pairs."""
    k = _parse_k()
    src = route_source(parse_filters(request.args), need_pickup_zone = True)
    where = src.with_conditions(*_known_zones("t.pu_zone_id", "t.do_zone_id"))
    rows = query(f"""
        SELECT t.pu_zone_id AS pu_zone_id, pz.zone AS pu_zone, pz.borough AS pu_borough,
               t.do_zone_id AS do_zone_id, dz.zone AS do_zone, dz.borough AS do_borough,
               {src.metrics['trips']} AS trips,
               {src.metrics['avg_fare']} AS avg_fare
        FROM {src.from_sql}
        JOIN zones dz ON dz.location_id = t.do_zone_id
        {where}
        GROUP BY t.pu_zone_id, t.do_zone_id """, src.params)
    ranked = top_k(rows, k, key=lambda r: (r["trips"], -r["pu_zone_id"], -r["do_zone_id"]))
    return {"data": ranked}
