#!/usr/bin/env python3
"""
Signal 12: Neighbor Effect

When one house on a street gets improvements, neighbors follow within
12-18 months. This layer detects clusters of recent home sales nearby —
a strong proxy for neighborhood renovation activity since new owners
are the most likely to invest in deck work.

Uses SANDAG parcel data only — no external API calls. The scan passes
all properties to this layer; it checks for nearby recent sales from
the same scan batch.
"""

import math
from datetime import date
from layers.base import BaseLayer


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# Module-level cache for all properties in the current scan
_all_properties = None


def set_scan_properties(properties):
    """Called by the scan pipeline to share all properties with this layer."""
    global _all_properties
    _all_properties = properties


class NeighborEffectLayer(BaseLayer):
    name  = "neighbor_effect"
    label = "Neighbor Effect"
    paid  = False

    SEARCH_RADIUS_M = 200
    RECENT_SALE_DAYS = 365  # neighbors who bought within last year

    def run(self, prop: dict) -> dict:
        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        if not _all_properties:
            return self._empty_result(detail="No scan data available for neighbor analysis")

        today = date.today()
        nearby_recent = []

        for other in _all_properties:
            if other is prop:
                continue
            olat = other.get("lat")
            olon = other.get("lon")
            if not olat or not olon:
                continue

            dist = _haversine_m(lat, lon, olat, olon)
            if dist > self.SEARCH_RADIUS_M or dist < 10:
                continue

            # Check if neighbor was recently sold
            sale_raw = other.get("sale_date")
            if not sale_raw:
                continue
            try:
                if isinstance(sale_raw, date):
                    sale_date = sale_raw
                else:
                    sale_date = date.fromisoformat(str(sale_raw)[:10])
                days_ago = (today - sale_date).days
                if days_ago <= self.RECENT_SALE_DAYS:
                    nearby_recent.append({
                        "address": other.get("address", ""),
                        "distance_m": round(dist),
                        "days_ago": days_ago,
                    })
            except (ValueError, TypeError):
                continue

        if not nearby_recent:
            return self._empty_result(detail="No recent home sales on neighboring properties")

        closest = min(nearby_recent, key=lambda x: x["distance_m"])
        count = len(nearby_recent)

        if count >= 3:
            score = 1.0
        elif count >= 2:
            score = 0.7
        else:
            score = 0.4

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"{count} neighbor(s) recently purchased — renovation activity likely",
            "data":   {
                "nearby_recent_sales": count,
                "closest_distance_m": closest["distance_m"],
                "closest_address": closest["address"][:40],
            },
            "paid":   self.paid,
        }
