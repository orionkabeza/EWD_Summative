from flask import Blueprint, jsonify, send_file

from backend.db import GEOJSON_PATH, query 
zones_bp = Blueprint("zones", __name__)

@zones_bp.route("", strict_slashes=False)
def list_zones():
    rows = query("""
        SELECT location_id, borough, zone, service_zone, centroid_lat, centroid_lon
        FROM zones ORDER BY location_id
    """)
    return jsonify({"data": rows})

@zones_bp.route("/geojson")
def geojson_zones():
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(
            f"{GEOJSON_PATH} not found. Run 'python pipeline/run_pipeline.py' first.")
    return send_file(GEOJSON_PATH, mimetype="application/geo+json")
