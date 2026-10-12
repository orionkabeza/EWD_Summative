from flask import Blueprint, jsonify, request

from backend.db import query, query_one
from backend.filters import FilterError, active_groups, parse_filters, solo_filters, where_clause, zone_source

trips_bp = Blueprint("trips", __name__)

SORTABLE_COLUMNS = {"pickup_ts", "trip_distance", "fare_amount"}
DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE = 25, 100

SMALL_RESULT_ROWS = 100_000

_COUNT_CACHE = {}


def list_sql(where, inner_order, outer_order):
    return f"""
    SELECT t.trip_id, t.pickup_ts, t.dropoff_ts, t.passenger_count, t.trip_distance,
           t.fare_amount, t.tip_amount, t.total_amount, t.trip_duration_min,
           t.avg_speed_mph, t.fare_per_mile, t.tip_pct,
           pz.zone AS pu_zone, pz.borough AS pu_borough,
           dz.zone AS do_zone, dz.borough AS do_borough,
           pt.description AS payment_type
    FROM (
        SELECT t.* FROM trips t
        {where}
        ORDER BY {inner_order}
        LIMIT ? OFFSET ?
    ) t
    JOIN zones pz ON pz.location_id = t.pu_zone_id
    JOIN zones dz ON dz.location_id = t.do_zone_id
    JOIN payment_types pt ON pt.payment_type_id = t.payment_type_id
    ORDER BY {outer_order}
    """


def _positive_int(name, default, maximum=None):
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise FilterError(f"'{name}' must be an integer, got '{raw}'")
    if value < 1 or (maximum and value > maximum):
        raise FilterError(f"'{name}' must be between 1 and {maximum or 'infinity'}, got '{value}'")
    return value


def _count(filters):
    source = zone_source(filters)
    key = (source.from_sql, source.where, tuple(source.params))
    if key not in _COUNT_CACHE:
        if len(_COUNT_CACHE) > 500:
            _COUNT_CACHE.clear()
        row = query_one(f"SELECT {source.metrics['trips']} AS n FROM {source.from_sql} {source.where}",
                        source.params)
        _COUNT_CACHE[key] = row["n"] or 0  # SUM() over zero rows is NULL
    return _COUNT_CACHE[key]


def _broad_groups(filters, total):
    groups = active_groups(filters)
    if total > SMALL_RESULT_ROWS:
        return set(groups)
    broad = set()
    for group in groups:
        solo = solo_filters(filters, group)
        if zone_source(solo).kind == "raw":
            continue
        if _count(solo) > SMALL_RESULT_ROWS:
            broad.add(group)
    return broad


def _inner_order(sort, direction, use_filter_index):
    prefix = "+" if use_filter_index else ""
    return f"{prefix}t.{sort} {direction}, t.trip_id {direction}"


@trips_bp.route("", strict_slashes=False)
def list_trips():
    filters = parse_filters(request.args)

    sort = request.args.get("sort", "pickup_ts")
    if sort not in SORTABLE_COLUMNS:
        raise FilterError(f"'sort' must be one of {sorted(SORTABLE_COLUMNS)}")
    order = request.args.get("order", "asc").lower()
    if order not in ("asc", "desc"):
        raise FilterError("'order' must be 'asc' or 'desc'")
    page = _positive_int("page", 1)
    page_size = _positive_int("page_size", DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)

    total = _count(filters)
    broad = _broad_groups(filters, total)
    use_filter_index = len(broad) < len(active_groups(filters))
    where, params = where_clause(filters, suppress_groups=broad, sort_column=sort)
    offset = (page - 1) * page_size
    direction = order.upper()
    if offset >= total:
        rows = []
    else:
        rows = query(
            list_sql(where, _inner_order(sort, direction, use_filter_index), f"t.{sort} {direction}, t.trip_id {direction}"),
            params + [page_size, offset]
        )

    return jsonify({"data": rows, "total": total, "page": page, "page_size": page_size})

@trips_bp.route("/<int:trip_id>")
def trip_detail(trip_id):
    row = query_one(
        """
        SELECT t.*,
               pz.zone AS pu_zone, pz.borough AS pu_borough,
               dz.zone AS do_zone, dz.borough AS do_borough,
               pt.description AS payment_type, rc.description AS rate_code, v.name AS vendor_name
        FROM trips t
        JOIN zones pz on pz.location_id = t.pu_zone_id
        JOIN zones dz on dz.location_id = t.do_zone_id
        JOIN payment_types pt ON pt.payment_type_id = t.payment_type_id
        JOIN rate_codes rc ON rc.rate_code_id = t.rate_code_id
        JOIN vendors v ON v.vendor_id = t.vendor_id
        WHERE t.trip_id = ?
        """,
        [trip_id]
    )
    if not row:
        return jsonify({"error": f"Trip {trip_id} not found"}), 404
    return jsonify(row)
