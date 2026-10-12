# NYC Taxi Pulse: Urban Mobility Data Explorer

A full-stack dashboard that explores New York City yellow-taxi trips (January 2019, about 7.67 million raw trips). A Python pipeline cleans and enriches the data, SQLite stores it, a Flask API serves it, and a browser dashboard lets you filter, chart and map urban mobility patterns.

- **Video walkthrough:** `<ADD LINK HERE>`
- **Team:** see the team participation sheet submitted with the assignment.

## What it does

| Layer | What | Where |
|---|---|---|
| Pipeline | Streams the 656 MB CSV in chunks, removes bad records (each logged with a reason), adds derived features, reprojects the zone shapefile to GeoJSON | `pipeline/` |
| Database | Normalised SQLite schema (fact table + 4 lookup tables), indexes, and pre-aggregated roll-up tables for fast dashboards | `database/` |
| Backend | Flask JSON API: filterable/sortable trips, aggregates, rankings | `backend/` |
| Algorithm | Hand-written min-heap and Top-K ranking (no `heapq`, no `sort`) | `backend/algorithms/` |
| Frontend | Filters, KPIs, charts, zone map, trip explorer (vanilla JS, Chart.js, Leaflet) | `frontend/` |

## Requirements

- Python 3.11 or newer
- An internet connection when viewing the dashboard (Chart.js, Leaflet and map tiles load from CDNs)
- About 5 GB of free disk space during the build (raw data 0.7 GB, cleaned CSV 0.9 GB, database about 2.1 GB, plus temporary space while SQLite builds indexes). After the build the cleaned CSV can be deleted.

## Setup and run

All commands are run from the project root.

**1. Install dependencies**

```bash
python -m venv venv
# Windows:      venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
```

**2. Add the raw data** (too large for GitHub). Download the three dataset files from the assignment page on Canvas and place them in `data/raw/`:

```
data/raw/yellow_tripdata_2019-01.csv
data/raw/taxi_zone_lookup.csv
data/raw/taxi_zones/            (the shapefile folder: .shp .dbf .shx .prj ...)
```

**3. Run the pipeline** (cleans the trips and builds the zone files)

```bash
python pipeline/run_pipeline.py
```

For a quick trial on the first 200,000 rows add `--sample 200000`. The full run reads every chunk and prints how many rows were kept and excluded per rule. Outputs: `data/processed/trips_clean.csv`, `data/processed/zones.csv`, `data/processed/taxi_zones.geojson`, `logs/excluded_records.csv`, `logs/exclusion_summary.json`.

**4. Build the database**

```bash
python database/load_db.py
```

This creates `database/urban_mobility.db` (schema, lookups, trips, indexes, then the roll-up tables) and reports any foreign-key violations (expected: 0). For the full file it takes several minutes; the database ends up around 2 GB, so make sure there is disk space.

**5. Start the app**

```bash
python backend/app.py
```

Open <http://127.0.0.1:5000>. The same server hosts the API and the dashboard. When it starts it runs the dashboard's opening queries once in the background (about 2 seconds), so the first visit is fast.

Optional environment variables (see `.env.example`): `PORT` (default 5000), `QUERY_TIME_LIMIT` (seconds a single query may run before it is stopped and the page asks for narrower filters; default 15, `0` = no limit), `WARM_UP` (`0` turns the start-up warm-up off).

## Tests

```bash
pytest backend/tests
```

Covers every cleaning rule, the heap and Top-K, and the API (against a tiny temporary database, so it does not need the real data).

## Performance note

The full file is 7.46 million trips, and grouping the raw table took 4 to 19 seconds per chart. `database/rollups.sql` therefore builds small pre-summed tables (by zone and hour, by route and hour, by route and day, plus distance/fare-banded versions), and `backend/filters.py` answers each request from the smallest table that gives an exact answer, falling back to the raw table only when it must. The dashboard's distance and fare controls offer the band edges the roll-ups are built on (for example "5 mi or more", "under $20"). Any other value, such as `min_distance=2.5`, still works through the API but scans the raw table and takes a few seconds. The route charts also use the raw table when a date range is combined with an hour, distance or fare filter (about 3-7 seconds). The other cards appear first. Any query running longer than `QUERY_TIME_LIMIT` is stopped and the page explains why.

## API summary

All endpoints accept the same filters: `start`, `end` (YYYY-MM-DD), `hour_min`, `hour_max` (0-23), `min_distance`, `max_distance`, `min_fare`, `max_fare`, `pu_borough`, `payment_type_id`.

| Endpoint | Returns |
|---|---|
| `GET /api/trips` | Paginated trips. Extra params: `sort` (`pickup_ts`, `trip_distance`, `fare_amount`), `order`, `page`, `page_size` (max 100) |
| `GET /api/trips/<id>` | One trip with zone, payment, rate code and vendor names |
| `GET /api/zones`, `/api/zones/geojson` | Zone table; zone polygons |
| `GET /api/analytics/summary` | KPI totals and averages |
| `GET /api/analytics/hourly`, `/daily`, `/borough`, `/payment-types` | Grouped aggregates |
| `GET /api/analytics/zone-counts` | Pickups per zone (colours the map) |
| `GET /api/analytics/top-zones?k=&by=pickup\|dropoff` | Top-K zones |
| `GET /api/analytics/top-routes?k=` | Top-K pickup-to-dropoff routes |

Errors return JSON `{"error": "..."}` with status 400 (bad parameter), 404, 503 (data not built yet) or 504 (the query ran longer than `QUERY_TIME_LIMIT`).

## Database

Schema: `database/schema.sql`. Indexes: `database/indexes.sql`. Example queries: `database/queries.sql`.
A small shareable dump (full schema plus the first 1,000 trips) is in `database/dump/`; regenerate it with `python database/make_sample_dump.py`.

## Project structure

```
data/raw/            raw inputs (not committed)
data/processed/      pipeline outputs (generated; only taxi_zones.geojson may be committed)
pipeline/            load_raw, clean, exclusion_log, features, zones, run_pipeline, config
database/            schema.sql, indexes.sql, load_db.py, queries.sql, make_sample_dump.py, dump/
backend/             app.py, db.py, filters.py, routes/, algorithms/, tests/
frontend/            index.html, css/, js/
logs/                excluded_records.csv, exclusion_summary.json (generated)
docs/                technical report, architecture diagram
```

## Troubleshooting

- **"Database not found"**: run steps 3 and 4 first.
- **Dashboard shows an error banner**: the backend is not running, or the database has not been built.
- **Map has no background**: map tiles need internet access.
