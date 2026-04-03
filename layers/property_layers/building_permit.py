#!/usr/bin/env python3
"""
Signal 2: Building Permit Adjacent (Pool/Spa)

When someone applies for a pool or spa permit, they are in "construction mode"
and have likely secured financing. A pool almost always needs a surrounding deck.
Queries San Diego Open Data (Socrata API — free, no key needed).
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


class BuildingPermitLayer(BaseLayer):
    name  = "building_permit"
    label = "Pool/Spa Permit"
    paid  = False

    def run(self, prop: dict) -> dict:
        if not requests:
            return self._empty_result(detail="requests library not available")

        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        cutoff = (date.today() - timedelta(days=config.PERMIT_LOOKBACK_DAYS)).isoformat()
        radius = config.PERMIT_SEARCH_RADIUS_M

        # Query Socrata for pool/spa permits with pagination
        s, w, n, e = config.CITY_BBOX
        bbox_filter = (
            f"latitude >= {s} AND latitude <= {n} AND "
            f"longitude >= {w} AND longitude <= {e}"
        )
        permits = []
        offset = 0
        page_size = 1000
        try:
            while True:
                params = {
                    "$where": (
                        f"approval_date >= '{cutoff}' AND "
                        f"{bbox_filter} AND "
                        f"("
                        f"upper(description) like '%POOL%' OR "
                        f"upper(description) like '%SPA%' OR "
                        f"upper(description) like '%SWIM%' OR "
                        f"upper(description) like '%HOT TUB%' OR "
                        f"upper(description) like '%OUTDOOR KITCHEN%'"
                        f")"
                    ),
                    "$limit": page_size,
                    "$offset": offset,
                }
                resp = requests.get(config.SD_OPEN_DATA_PERMITS, params=params, timeout=15)
                resp.raise_for_status()
                page = resp.json()
                permits.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size
        except Exception as e:
            return self._empty_result(detail=f"Permit query failed: {e}")

        if not permits:
            return self._empty_result(detail="No recent pool/spa permits in area")

        # Find closest permit to this property
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
                detail=f"Nearest pool/spa permit is {closest_dist:.0f}m away (>{radius}m radius)"
            )

        # Score decays with distance
        if closest_dist < 50:
            score = 1.0
        else:
            score = self._clamp(1.0 - (closest_dist / radius) * 0.7)

        desc = (closest_permit or {}).get("description", "Pool/Spa permit")[:80]
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"Pool/spa permit {closest_dist:.0f}m away — owner in construction mode",
            "data":   {
                "permit_distance_m": round(closest_dist),
                "permit_description": desc,
            },
            "paid":   self.paid,
        }
