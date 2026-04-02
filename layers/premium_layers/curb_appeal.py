#!/usr/bin/env python3
"""
Signal 10: Curb Appeal / Stale Listing (PREMIUM)

Finds homes that have been on the market 60+ days — desperate sellers.
If photos show a gray, weathered deck, reach out to the listing agent
with a "Weekend Refresh" package.

Requires: RapidAPI key for Zillow/Redfin API access.
"""

from layers.base import BaseLayer
import config

try:
    import requests as req_lib
except ImportError:
    req_lib = None


class CurbAppealLayer(BaseLayer):
    name  = "curb_appeal"
    label = "Curb Appeal"
    paid  = True

    def run(self, prop: dict) -> dict:
        api_key = config.RAPIDAPI_KEY
        if not api_key:
            return self._paid_stub()

        if not req_lib:
            return self._empty_result(detail="requests library not available")

        lat = prop.get("lat")
        lon = prop.get("lon")
        address = prop.get("address", "")
        if not (lat and lon) and not address:
            return self._empty_result(detail="No location data available")

        try:
            # Query Zillow via RapidAPI for listing data
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
            }
            params = {}
            if address:
                params["address"] = address
            else:
                params["lat"] = lat
                params["lng"] = lon

            resp = req_lib.get(
                "https://zillow-com1.p.rapidapi.com/property",
                headers=headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return self._empty_result(detail=f"Listing API query failed: {e}")

        # Check if property is listed and for how long
        days_on_market = data.get("daysOnZillow") or data.get("timeOnZillow", 0)
        if isinstance(days_on_market, str):
            try:
                days_on_market = int(days_on_market)
            except ValueError:
                days_on_market = 0

        if days_on_market < config.STALE_LISTING_DAYS:
            return self._empty_result(
                detail=f"Listed {days_on_market} days — not stale yet (threshold: {config.STALE_LISTING_DAYS}d)"
            )

        # Stale listing detected
        listing_price = data.get("price", 0)
        has_photos = bool(data.get("imgSrc") or data.get("photos"))

        if has_photos and days_on_market > 90:
            score = 1.0
            detail = f"Stale listing ({days_on_market}d) with photos — pitch Weekend Refresh to agent"
        elif days_on_market > 90:
            score = 0.8
            detail = f"Stale listing ({days_on_market}d) — seller likely motivated"
        else:
            score = 0.7
            detail = f"Listed {days_on_market} days — approaching stale threshold"

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "days_on_market": days_on_market,
                "listing_price": listing_price,
                "has_photos": has_photos,
            },
            "paid":   self.paid,
        }
