import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from backend.db import QueryTimeout 
from backend.filters import FilterError
from backend.routes.trips import trips_bp
from backend.routes.zones import zones_bp


FRONTEND_DIR = ROOT / "frontend" 

try:
    from backend.routes.analytics import analytics_bp
except ImportError as error:

    analytics_bp = None
    print(f"WARNING: analytics endpoints are not available ({error})" , file=sys.stderr)

WARM_UP_PATHS = [
    "/api/zones",
    "/api/zones/geojson",
    "/api/analytics/summary",
    "/api/analytics/hourly",
    "/api/analytics/daily",
    "/api/analytics/borough",
    "/api/analytics/payment-types",
    "/api/analytics/zone-counts",
    "/api/analytics/top-zones?k=10&by=pickup",
    "/api/analytics/top-zones?k=10&by=dropoff",
    "/api/analytics/top-routes?k=10",
    "/api/trips?sort=pickup_ts&order=desc&page=1&page_size=25"
]   


def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(trips_bp, url_prefix="/api/trips")
    app.register_blueprint(zones_bp, url_prefix="/api/zones")
    if analytics_bp is not None:
       app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")


    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(FilterError)
    def bad_request(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(QueryTimeout)
    def query_timeout(error):  
        return jsonify({"error": str(error)}), 504

    @app.errorhandler(FileNotFoundError)
    def missing_file(error):
        return jsonify({"error": str(error)}), 503

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    return app


def warm_up(flask_app, paths=WARM_UP_PATHS):
    results = []
    with flask_app.test_client() as client:
        for path in paths:
            started = time.monotonic()
            status = client.get(path).status_code
            results.append((path, status, round(time.monotonic() - started, 2)))
    return results


def start_warm_up(flask_app):

    def run():
        started = time.monotonic()
        results = warm_up(flask_app)
        failed = [f"{path} ({status})" for path, status, _ in results if status != 200]
        print(f"Warm-up finished in {time.monotonic() - started:.1f}s"
              + (f"; not available: {', '.join(failed)}" if failed else ""), file=sys.stderr)
    threading.Thread(target=run, name="warm-up", daemon=True).start()


app = create_app()

if  __name__ == "__main__":
     if os.environ.get("WARM_UP", "1") != "0":
        start_warm_up(app)
     app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
