#!/usr/bin/env python3
"""
Signal 3: Dated Deck Permit

Checks for deck/patio/balcony permits issued 10+ years ago.
A permit from 2010 means that deck is now 16 years old — likely needs
replacement or major repair.
"""

import math
from datetime import date
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


class DeckPermitAgeLayer(BaseLayer):
    name  = "deck_permit_age"
    label = "Dated Deck Permit"
    paid  = False

    def run(self, prop: dict) -> dict:
        if not requests:
            return self._empty_result(detail="requests library not available")

        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        min_age = config.DECK_PERMIT_AGE_YEARS
        cutoff_year = date.today().year - min_age
        radius = config.PERMIT_SEARCH_RADIUS_M

        # Query Socrata for old deck permits with pagination and bbox
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
                        f"approval_date <= '{cutoff_year}-12-31' AND "
                        f"{bbox_filter} AND "
                        f"("
                        f"upper(description) like '%DECK%' OR "
                        f"upper(description) like '%PATIO%' OR "
                        f"upper(description) like '%BALCON%' OR "
                        f"upper(description) like '%PORCH%' OR "
                        f"upper(description) like '%STAIR%'"
                        f")"
                    ),
                    "$limit": page_size,
                    "$offset": offset,
                    "$order": "approval_date ASC",
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
            return self._empty_result(detail="No dated deck permits found in area")

        # Find closest deck permit to this property
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
                detail=f"Nearest deck permit is {closest_dist:.0f}m away (>{radius}m radius)"
            )

        # Calculate permit age and score
        permit_date = (closest_permit or {}).get("approval_date", "")[:10]
        try:
            permit_year = int(permit_date[:4])
        except (ValueError, IndexError):
            permit_year = cutoff_year

        current_year = date.today().year
        permit_age = current_year - permit_year

        if permit_age >= 15:
            score = 1.0
            detail = f"Deck permit from {permit_year} ({permit_age} yrs) — likely needs full replacement"
        elif permit_age >= 10:
            score = 0.7
            detail = f"Deck permit from {permit_year} ({permit_age} yrs) — significant wear expected"
        elif permit_age >= 7:
            score = 0.4
            detail = f"Deck permit from {permit_year} ({permit_age} yrs) — maintenance due"
        else:
            return self._empty_result(
                detail=f"Deck permit from {permit_year} ({permit_age} yrs) — still relatively new"
            )

        desc = (closest_permit or {}).get("description", "Deck/patio permit")[:80]
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "permit_year": permit_year,
                "permit_age_years": permit_age,
                "permit_distance_m": round(closest_dist),
                "permit_description": desc,
            },
            "paid":   self.paid,
        }
