#!/usr/bin/env python3
"""
Signal 8: Commercial Outdoor Seating

Queries OSM for restaurants/cafes with outdoor_seating=yes tag.
Post-pandemic, restaurants added permanent outdoor decks — high-traffic
areas requiring constant maintenance. Pitch quarterly safety contracts.
"""

import time
from layers.base import BaseLayer
import config

try:
    import requests as req_lib
except ImportError:
    req_lib = None


def _overpass(query: str) -> dict:
    if not req_lib:
        return {"elements": []}
    for url in config.OVERPASS_FALLBACK_URLS:
        for attempt in range(2):
            try:
                resp = req_lib.post(
                    url,
                    data={"data": query},
                    timeout=config.OVERPASS_TIMEOUT + 10,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                if attempt == 0:
                    time.sleep(5)
    return {"elements": []}


class OutdoorSeatingLayer(BaseLayer):
    name  = "outdoor_seating"
    label = "Outdoor Seating"
    paid  = False

    def run(self, prop: dict) -> dict:
        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        # This layer scans the whole city bbox for restaurants with outdoor seating
        # so it runs once per city (results cached in prop if already run)
        if prop.get("_outdoor_seating_scanned"):
            return self._empty_result(detail="Already scanned for this batch")

        s, w, n, e = config.CITY_BBOX
        query = f"""
        [out:json][timeout:{config.OVERPASS_TIMEOUT}];
        (
          node["amenity"~"restaurant|cafe|bar"]["outdoor_seating"="yes"]({s},{w},{n},{e});
          way["amenity"~"restaurant|cafe|bar"]["outdoor_seating"="yes"]({s},{w},{n},{e});
          node["amenity"~"restaurant|cafe|bar"]["outdoor_seating:type"]({s},{w},{n},{e});
        );
        out tags center;
        """

        data = _overpass(query)
        elements = data.get("elements", [])

        if not elements:
            return self._empty_result(detail="No restaurants with outdoor seating tagged in OSM")

        # For commercial signals, the "property" is actually each restaurant found
        name = ""
        for el in elements:
            tags = el.get("tags", {})
            if tags.get("name"):
                name = tags["name"]
                break

        score = 1.0 if len(elements) >= 3 else 0.7
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"{len(elements)} restaurant(s) with outdoor seating in area",
            "data":   {
                "restaurants_found": len(elements),
                "sample_name": name[:60],
            },
            "paid":   self.paid,
        }
