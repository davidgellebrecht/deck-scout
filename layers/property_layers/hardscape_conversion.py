#!/usr/bin/env python3
"""
Signal 14: Hardscape / Drought-Resistant Conversion

San Diego homeowners converting lawns to drought-resistant hardscape
often add or expand deck/patio areas at the same time. SD water
restrictions make this increasingly common.

Data: FREE — same Socrata permits API.
"""

import math
from datetime import date, timedelta
from layers.base import BaseLayer
import config

try:
    import requests
except ImportError:
    requests = None


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class HardscapeConversionLayer(BaseLayer):
    name  = "hardscape_conversion"
    label = "Hardscape Conversion"
    paid  = False

    def run(self, prop: dict) -> dict:
        if not requests:
            return self._empty_result(detail="requests library not available")

        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        cutoff = (date.today() - timedelta(days=365)).isoformat()
        radius = config.PERMIT_SEARCH_RADIUS_M
        s, w, n, e = config.CITY_BBOX
        bbox_filter = (
            f"latitude >= {s} AND latitude <= {n} AND "
            f"longitude >= {w} AND longitude <= {e}"
        )

        try:
            params = {
                "$where": (
                    f"approval_date >= '{cutoff}' AND "
                    f"{bbox_filter} AND "
                    f"("
                    f"upper(description) like '%LANDSCAPE%' OR "
                    f"upper(description) like '%HARDSCAPE%' OR "
                    f"upper(description) like '%DROUGHT%' OR "
                    f"upper(description) like '%XERISCAPE%' OR "
                    f"upper(description) like '%PAVER%' OR "
                    f"upper(description) like '%PATIO COVER%' OR "
                    f"upper(description) like '%PERGOLA%'"
                    f")"
                ),
                "$limit": 1000,
            }
            resp = requests.get(config.SD_OPEN_DATA_PERMITS, params=params, timeout=15)
            resp.raise_for_status()
            permits = resp.json()
        except Exception as e:
            return self._empty_result(detail=f"Permit query failed: {e}")

        if not permits:
            return self._empty_result(detail="No recent hardscape/landscaping permits in area")

        # Find closest permit on the same parcel
        closest_dist = float("inf")
        closest_permit = None
        for p in permits:
            plat = p.get("latitude") or p.get("lat")
            plon = p.get("longitude") or p.get("lon")
            if not plat or not plon:
                continue
            try:
                dist = _haversine_m(lat, lon, float(plat), float(plon))
            except (ValueError, TypeError):
                continue
            if dist < closest_dist:
                closest_dist = dist
                closest_permit = p

        if closest_dist > radius:
            return self._empty_result(
                detail=f"Nearest hardscape permit is {closest_dist:.0f}m away — outside same-parcel radius"
            )

        desc = (closest_permit or {}).get("description", "Hardscape/landscape permit")[:60]
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  0.8,
            "detail": f"Hardscape conversion in progress — {desc}",
            "data":   {
                "permit_distance_m": round(closest_dist),
                "permit_description": desc,
            },
            "paid":   self.paid,
        }
