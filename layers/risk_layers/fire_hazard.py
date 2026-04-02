#!/usr/bin/env python3
"""
Signal 5: Fire Hazard Severity Zones (FHSZ)

CA insurance companies are dropping homeowners in high-fire-risk areas.
Non-combustible decking (composite/aluminum) is often required to keep coverage.
Uses bundled CAL FIRE GeoJSON for offline point-in-polygon checks.
"""

import json
import os
from layers.base import BaseLayer
import config

_fhsz_data = None


def _load_fhsz():
    """Load and cache the FHSZ GeoJSON."""
    global _fhsz_data
    if _fhsz_data is not None:
        return _fhsz_data

    path = config.CALFIRE_FHSZ_GEOJSON
    if not os.path.exists(path):
        _fhsz_data = []
        return _fhsz_data

    try:
        from shapely.geometry import shape, Point
        with open(path, "r") as f:
            geojson = json.load(f)
        features = []
        for feat in geojson.get("features", []):
            geom = shape(feat["geometry"])
            props = feat.get("properties", {})
            severity = (
                props.get("SRA_FHSZ") or props.get("FHSZ_SRA")
                or props.get("HAZ_CODE") or props.get("HAZ_CLASS")
                or props.get("SEVERITY") or ""
            ).strip().upper()
            features.append({"geometry": geom, "severity": severity})
        _fhsz_data = features
    except Exception:
        _fhsz_data = []

    return _fhsz_data


def _severity_label(raw: str) -> str:
    raw = raw.upper()
    if "VERY HIGH" in raw or "VHFHSZ" in raw or raw == "3":
        return "Very High"
    if "HIGH" in raw or "HFHSZ" in raw or raw == "2":
        return "High"
    if "MODERATE" in raw or "MFHSZ" in raw or raw == "1":
        return "Moderate"
    return raw.title() if raw else "Unknown"


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

        try:
            from shapely.geometry import Point
            point = Point(float(lon), float(lat))
        except Exception:
            return self._empty_result(detail="Invalid coordinates")

        for feat in features:
            if feat["geometry"].contains(point):
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
