#!/usr/bin/env python3
"""
Signal 3: Dated Deck Permit (by property age)

Properties with aging decks based on year built. Since the SD Open Data
permit API is unreliable, this layer uses the property's year_built and
building type to infer deck age — homes built with decks 10+ years ago
likely need replacement.

This is a more reliable proxy than trying to match individual permits,
since SANDAG year_built data is comprehensive.
"""

from datetime import date
from layers.base import BaseLayer
import config


class DeckPermitAgeLayer(BaseLayer):
    name  = "deck_permit_age"
    label = "Dated Deck Permit"
    paid  = False

    def run(self, prop: dict) -> dict:
        year_built = prop.get("year_built")
        if not year_built:
            return self._empty_result(detail="No year-built data — cannot estimate deck age")

        try:
            year_built = int(year_built)
        except (ValueError, TypeError):
            return self._empty_result(detail="Invalid year-built data")

        current_year = date.today().year
        age = current_year - year_built

        # Homes built with original decks — estimate deck age = home age
        # This is more reliable than searching for individual permits
        min_age = config.DECK_PERMIT_AGE_YEARS

        if age < min_age:
            return self._empty_result(
                detail=f"Home is {age} years old — deck likely still in good condition"
            )

        # Only single-family homes and duplexes typically have private decks
        # (condos/apartments handled by SB-326 signal)
        btype = (prop.get("building_type") or "").lower()
        if btype in ("apartments", "condo", "mobile_home", "vacant_residential"):
            return self._empty_result(
                detail=f"{btype.title()} — deck age assessment handled by SB-326 signal"
            )

        if age >= 20:
            score = 1.0
            detail = f"Home built {year_built} ({age} yrs) — original deck likely unsafe, needs replacement"
        elif age >= 15:
            score = 0.8
            detail = f"Home built {year_built} ({age} yrs) — deck showing significant wear"
        elif age >= min_age:
            score = 0.5
            detail = f"Home built {year_built} ({age} yrs) — deck maintenance likely overdue"
        else:
            return self._empty_result(detail=f"Home is {age} years old — below threshold")

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "year_built": year_built,
                "estimated_deck_age": age,
            },
            "paid":   self.paid,
        }
