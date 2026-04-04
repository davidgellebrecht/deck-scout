#!/usr/bin/env python3
"""
Signal 12: Neighbor Effect / Deck Permit Clustering

When one house on a street gets a new deck, neighbors follow within
12-18 months ("keeping up with the Joneses"). This layer detects
RECENT deck permits NEAR the property — the inverse of DeckPermitAge
(which looks for OLD permits on the SAME property).

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


class NeighborEffectLayer(BaseLayer):
    name  = "neighbor_effect"
    label = "Neighbor Effect"
    paid  = False

    SEARCH_RADIUS_M = 200  # look for permits within 200m
    LOOKBACK_MONTHS = 18   # recent permits in last 18 months

    def run(self, prop: dict) -> dict:
        if not requests:
            return self._empty_result(detail="requests library not available")

        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        cutoff = (date.today() - timedelta(days=self.LOOKBACK_MONTHS * 30)).isoformat()
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
                    f"upper(description) like '%DECK%' OR "
                    f"upper(description) like '%PATIO%' OR "
                    f"upper(description) like '%BALCON%' OR "
                    f"upper(description) like '%PORCH%'"
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
            return self._empty_result(detail="No recent deck permits in surrounding area")

        # Find permits NEAR this property (but NOT on the same parcel — >30m away)
        nearby_permits = []
        for p in permits:
            plat = p.get("latitude") or p.get("lat")
            plon = p.get("longitude") or p.get("lon")
            if not plat or not plon:
                continue
            try:
                dist = _haversine_m(lat, lon, float(plat), float(plon))
            except (ValueError, TypeError):
                continue
            # Must be nearby (within 200m) but NOT the same parcel (>30m)
            if 30 < dist <= self.SEARCH_RADIUS_M:
                nearby_permits.append({"permit": p, "distance_m": dist})

        if not nearby_permits:
            return self._empty_result(detail="No recent deck permits on neighboring properties")

        # Score by proximity and count
        closest = min(nearby_permits, key=lambda x: x["distance_m"])
        dist = closest["distance_m"]

        if dist <= 50 and len(nearby_permits) >= 2:
            score = 1.0
        elif dist <= 100:
            score = 0.7
        else:
            score = 0.4

        desc = (closest["permit"].get("description") or "Deck permit")[:60]
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"{len(nearby_permits)} neighbor(s) got deck work recently — closest {dist:.0f}m away",
            "data":   {
                "nearby_permits_count": len(nearby_permits),
                "closest_distance_m": round(dist),
                "closest_description": desc,
            },
            "paid":   self.paid,
        }
