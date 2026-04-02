#!/usr/bin/env python3
"""
Signal 6: Safety Violation

Checks city Code Enforcement / Building Safety logs for violations related
to decks, balconies, stairs, or unsafe structures. Property owners with
violations need a solution provider to clear city fines.
"""

import math
from datetime import date, timedelta
from layers.base import BaseLayer
import config

try:
    import requests as req_lib
except ImportError:
    req_lib = None


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class SafetyViolationLayer(BaseLayer):
    name  = "safety_violation"
    label = "Safety Violation"
    paid  = False

    def run(self, prop: dict) -> dict:
        if not req_lib:
            return self._empty_result(detail="requests library not available")

        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        months = config.CODE_ENFORCEMENT_MONTHS
        cutoff = (date.today() - timedelta(days=months * 30)).isoformat()

        try:
            params = {
                "$where": (
                    f"date_case_created >= '{cutoff}' AND "
                    f"("
                    f"upper(case_type) like '%DECK%' OR "
                    f"upper(case_type) like '%BALCON%' OR "
                    f"upper(case_type) like '%STAIR%' OR "
                    f"upper(case_type) like '%UNSAFE%' OR "
                    f"upper(case_type) like '%STRUCT%' OR "
                    f"upper(case_type) like '%HABITAB%' OR "
                    f"upper(violation_name) like '%DECK%' OR "
                    f"upper(violation_name) like '%BALCON%' OR "
                    f"upper(violation_name) like '%STAIR%' OR "
                    f"upper(violation_name) like '%ROT%'"
                    f")"
                ),
                "$limit": 100,
            }
            resp = req_lib.get(
                config.SD_OPEN_DATA_CODE_ENFORCEMENT,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            cases = resp.json()
        except Exception as e:
            return self._empty_result(detail=f"Code enforcement query failed: {e}")

        if not cases:
            return self._empty_result(detail="No relevant code enforcement cases found")

        # Find closest case to this property
        closest_dist = float("inf")
        closest_case = None
        for c in cases:
            clat = c.get("latitude") or c.get("lat")
            clon = c.get("longitude") or c.get("lon")
            if not clat or not clon:
                continue
            try:
                dist = _haversine_m(lat, lon, float(clat), float(clon))
            except (ValueError, TypeError):
                continue
            if dist < closest_dist:
                closest_dist = dist
                closest_case = c

        if closest_dist > config.PERMIT_SEARCH_RADIUS_M:
            return self._empty_result(
                detail=f"Nearest violation is {closest_dist:.0f}m away — outside search radius"
            )

        # Active violations score higher than closed ones
        status = (closest_case or {}).get("case_status", "").upper()
        case_type = (closest_case or {}).get("case_type", "") or (closest_case or {}).get("violation_name", "")

        if "OPEN" in status or "ACTIVE" in status:
            score = 1.0
            detail = f"Active safety violation — {case_type[:50]}"
        else:
            score = 0.7
            detail = f"Recently closed violation — {case_type[:50]}"

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "violation_distance_m": round(closest_dist),
                "case_status": status,
                "case_type": case_type[:80],
            },
            "paid":   self.paid,
        }
