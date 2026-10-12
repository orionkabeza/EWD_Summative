"""Taxi-zone metadata: join the lookup table with the shapefile geometry.

outputs
-------
data/processed/taxi_zones.geojson : WGS84 polygons for the leaflet map
data/processed/zones.csv          : one row per LocationID with a centroid

Facts about the raw files that this modile handles (verified on the data):
* The shapefile is in NY State Plane (feet), not lat/lon, so it is reprojected.
* LocationIDs 56 and 103 appear in omre than one shapefile record (a zone made of several pieces), so records are merged per LocationID.
* LocationIDs 57, 104, 105, 264 and 265 exist in the lookup but have no polygon.
  They keep a row in zones.csv (trips can still reference them) with an empty
  centroid, and are reported by ``build_zones``.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import shapefile  # noqa: E402 (psyshp)
from pyproj import CRS, Transformer # noqa:E402
from shapely.geometry import mapping,shape # noqa: E402
from shapely.ops import transform, unary_union # noqa:E402
import shapely # noqa: E402

from pipeline import config as cfg # noqa: E402
from pipeline.load_raw import load_zone_lookup #noqa: E402

TARGET_CRS = "EPSG:4326"
SIMPLIFY_TOLERANCE_DEG = 0.0001 # about 10 m; keeps the GeoJSON light for the browser


def _source_crs():
    """Read the crs from the shapefile's own .prj so we never guess the projection."""
    prj_path = cfg.ZONE_SHAPEFILE.with_suffix(".prj")
    return CRS.from_wkt(prj_path.read_text())


def _merged_geometries():
    """Return {location_id: shapely geometry (source CRS)}, merging split records."""
    reader = shapefile.Reader(str(cfg.ZONE_SHAPEFILE))
    pieces = {}
    for shape_record in reader.shapeRecords():
        location_id = int(shape_record.record["LocationID"])
        pieces.setdefault(location_id,[]).append(shape(shape_record.shape.__geo_interface__))
    return {location_id: unary_union(parts) for location_id, parts in pieces.items()}


def build_zones():
    """Build zones.csv and taxi_zones.geojson. Returns a small summary dict."""
    lookup = load_zone_lookup()
    # The lookup spells missing values as the text "N/A", which pandas reads as NaN.
    lookup["borough"] = lookup["borough"].fillna("Unknown")
    lookup["zone"] = lookup["zone"].fillna("Unknown")
    lookup["service_zone"] = lookup["service_zone"].fillna("Unknown")

    to_wgs84 = Transformer.from_crs(_source_crs(), TARGET_CRS, always_xy=True).transform
    geometries = _merged_geometries()

    centroid_lat, centroid_lon, features = {}, {}, []
    for row in lookup.itertuples(index=False):
        geometry = geometries.get(row.location_id)
        if geometry is None:
            continue
        # Centroid is computed in the projected (metric-like) CRS, then converted.
        lon, lat = to_wgs84(geometry.centroid.x, geometry.centroid.y)
        centroid_lat[row.location_id], centroid_lon[row.location_id] = round(lat, 6), round(lon, 6)

        wgs84_geometry = transform(to_wgs84, geometry).simplify(
            SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
        wgs84_geometry = shapely.set_precision(wgs84_geometry, 1e-5)
        features.append({
            "type": "Feature",
            "properties": {
                "location_id": int(row.location_id),
                "zone": row.zone,
                "borough": row.borough,
                "service_zone": row.service_zone,
            },
            "geometry": mapping(wgs84_geometry),
        })

    lookup["centroid_lat"] = lookup["location_id"].map(centroid_lat)
    lookup["centroid_lon"] = lookup["location_id"].map(centroid_lon)

    cfg.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(cfg.ZONES_CSV, index=False)
    with open(cfg.ZONES_GEOJSON, "w", encoding="utf-8") as handle:
        json.dump({"type": "FeatureCollection", "features": features}, handle)

    return {
        "zones_in_lookup": int(len(lookup)),
        "zones_with_polygon": len(features),
        "lookup_ids_without_polygon": sorted(
            int(i) for i in set(lookup["location_id"]) - set(geometries)),
    }


if __name__ == "__main__":
    print(build_zones())

