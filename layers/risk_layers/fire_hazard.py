#!/usr/bin/env python3
"""
Signal 5: Fire Hazard Severity Zones (FHSZ)

CA insurance companies are dropping homeowners in high-fire-risk areas.
Non-combustible decking (composite/aluminum) is often required to keep coverage.
Uses bundled CAL FIRE GeoJSON for offline point-in-polygon checks.

Works with or without shapely — includes a pure-Python fallback.
"""

import json
import os
from layers.base import BaseLayer
import config

_fhsz_data = None
_use_shapely = False


def _point_in_polygon_pure(px, py, polygon_coords):
    """Ray-casting point-in-polygon test — pure Python, no shapely needed."""
    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _load_fhsz():
    """Load and cache the FHSZ GeoJSON."""
    global _fhsz_data, _use_shapely
    if _fhsz_data is not None:
        return _fhsz_data

    path = config.CALFIRE_FHSZ_GEOJSON
    if not os.path.exists(path):
        _fhsz_data = []
        return _fhsz_data

    try:
        with open(path, "r") as f:
            geojson = json.load(f)
    except Exception:
        _fhsz_data = []
        return _fhsz_data

    # Try shapely first (faster for many points)
    try:
        from shapely.geometry import shape
        _use_shapely = True
    except ImportError:
        _use_shapely = False

    features = []
    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        geom_data = feat.get("geometry", {})

        # Get severity — try HAZ_CLASS first (human-readable), then HAZ_CODE
        haz_class = str(props.get("HAZ_CLASS", "") or "").strip()
        haz_code = str(props.get("HAZ_CODE", "") or "").strip()
        severity = haz_class or haz_code

        entry = {"severity": severity}

        if _use_shapely:
            try:
                entry["geometry"] = shape(geom_data)
            except Exception:
                continue
        else:
            # Store raw polygon coordinates for pure-Python fallback
            geom_type = geom_data.get("type", "")
            coords = geom_data.get("coordinates", [])
            if geom_type == "Polygon" and coords:
                entry["rings"] = coords  # list of rings
            elif geom_type == "MultiPolygon" and coords:
                entry["multi_rings"] = coords  # list of polygon ring sets
            else:
                continue

        features.append(entry)

    _fhsz_data = features
    return _fhsz_data


def _severity_label(raw):
    raw = str(raw).upper()
    if "VERY HIGH" in raw or raw == "3":
        return "Very High"
    if "HIGH" in raw or raw == "2":
        return "High"
    if "MODERATE" in raw or raw == "1":
        return "Moderate"
    return raw.title() if raw else "Unknown"


def _point_in_feature(lon, lat, feat):
    """Check if point (lon, lat) is inside a feature."""
    if _use_shapely:
        from shapely.geometry import Point
        return feat["geometry"].contains(Point(lon, lat))
    else:
        # Pure Python — check each ring
        if "rings" in feat:
            for ring in feat["rings"]:
                if _point_in_polygon_pure(lon, lat, ring):
                    return True
        elif "multi_rings" in feat:
            for polygon_rings in feat["multi_rings"]:
                for ring in polygon_rings:
                    if _point_in_polygon_pure(lon, lat, ring):
                        return True
        return False


class FireHazardLayer(BaseLayer):
    name  = "fire_hazard"
    label = "Fire Hazard Zone"
    paid  = False

    def run(self, prop: dict) -> dict:
        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        features = _load_fhsz()
        if not features:
            return self._empty_result(
                detail="FHSZ data not available — place sd_county_fhsz.geojson in data/"
            )

        lat = float(lat)
        lon = float(lon)

        for feat in features:
            if _point_in_feature(lon, lat, feat):
                severity = _severity_label(feat["severity"])
                if "VERY HIGH" in severity.upper():
                    score = 1.0
                elif "HIGH" in severity.upper():
                    score = 0.7
                elif "MODERATE" in severity.upper():
                    score = 0.3
                else:
                    score = 0.5

                return {
                    "layer":  self.name,
                    "label":  self.label,
                    "signal": True,
                    "score":  score,
                    "detail": f"{severity} fire hazard zone — non-combustible decking recommended",
                    "data":   {"fhsz_severity": severity},
                    "paid":   self.paid,
                }

        return self._empty_result(detail="Not in a fire hazard severity zone")
