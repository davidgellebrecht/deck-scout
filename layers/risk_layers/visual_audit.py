#!/usr/bin/env python3
"""
Signal 7: Visual Audit (OSM)

Queries OpenStreetMap for building material tags, deck/patio features,
and construction dates near the property. Free alternative to Street View AI.
"""

import time
from layers.base import BaseLayer
import config

try:
    import requests as req_lib
except ImportError:
    req_lib = None


def _overpass(query: str) -> dict:
    """POST an Overpass QL query with retry and fallback."""
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


class VisualAuditLayer(BaseLayer):
    name  = "visual_audit"
    label = "Visual Audit (OSM)"
    paid  = False

    def run(self, prop: dict) -> dict:
        lat = prop.get("lat")
        lon = prop.get("lon")
        if not lat or not lon:
            return self._empty_result(detail="No coordinates available")

        # Search a small radius around the property for building features
        radius = 100  # metres

        query = f"""
        [out:json][timeout:{config.OVERPASS_TIMEOUT}];
        (
          way["building:material"](around:{radius},{lat},{lon});
          way["building:material"="wood"](around:{radius},{lat},{lon});
          node["man_made"="deck"](around:{radius},{lat},{lon});
          way["man_made"="deck"](around:{radius},{lat},{lon});
          node["leisure"="patio"](around:{radius},{lat},{lon});
          way["leisure"="patio"](around:{radius},{lat},{lon});
          way["building:levels"](around:{radius},{lat},{lon});
          way["start_date"](around:{radius},{lat},{lon});
        );
        out tags center;
        """

        data = _overpass(query)
        elements = data.get("elements", [])

        if not elements:
            # No OSM data = no signal (can't confirm deck condition)
            return self._empty_result(
                detail="No building material data in OSM — insufficient data to assess"
            )

        # Analyse found elements
        has_wood = False
        has_deck = False
        oldest_date = None

        for el in elements:
            tags = el.get("tags", {})
            material = tags.get("building:material", "").lower()
            if "wood" in material or "timber" in material:
                has_wood = True
            if tags.get("man_made") == "deck" or tags.get("leisure") == "patio":
                has_deck = True
            start = tags.get("start_date", "")
            if start and (oldest_date is None or start < oldest_date):
                oldest_date = start

        if has_wood and has_deck:
            score = 1.0
            detail = "Wood structure with deck/patio features detected in OSM"
        elif has_wood:
            score = 0.8
            detail = "Wood building material detected — likely has aging deck"
        elif has_deck:
            score = 0.7
            detail = "Deck/patio feature tagged in OSM"
        else:
            score = 0.5
            detail = f"Building data found in OSM ({len(elements)} features)"

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "osm_elements_found": len(elements),
                "has_wood_tags": has_wood,
                "has_deck_tags": has_deck,
                "oldest_date": oldest_date,
            },
            "paid":   self.paid,
        }
