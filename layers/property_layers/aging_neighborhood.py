#!/usr/bin/env python3
"""
Signal 4: Aging Neighborhood Strategy

Pure math on the year_built field — no external API calls.
Pressure-treated wood decks start looking rough after 15-20 years.
Homes built 2000-2013 are in the deck replacement cycle.
"""

from datetime import date
from layers.base import BaseLayer


class AgingNeighborhoodLayer(BaseLayer):
    name  = "aging_neighborhood"
    label = "Aging Deck"
    paid  = False

    def run(self, prop: dict) -> dict:
        year_built = prop.get("year_built")
        if not year_built:
            return self._empty_result(detail="No year-built data available")

        try:
            year_built = int(year_built)
        except (ValueError, TypeError):
            return self._empty_result(detail="Invalid year-built data")

        current_year = date.today().year
        age = current_year - year_built

        # Primary band: 16-26 years old (built 2000-2010) — prime replacement
        if 2006 <= year_built <= 2010:
            score = 1.0
            detail = f"Built {year_built} ({age} yrs old) — prime deck replacement window"
        elif 2000 <= year_built <= 2005:
            score = 0.8
            detail = f"Built {year_built} ({age} yrs old) — deck likely overdue for replacement"
        elif 2011 <= year_built <= 2013:
            score = 0.5
            detail = f"Built {year_built} ({age} yrs old) — deck maintenance likely due soon"
        else:
            return self._empty_result(
                detail=f"Built {year_built} ({age} yrs old) — outside target age range"
            )

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {"year_built": year_built, "home_age_years": age},
            "paid":   self.paid,
        }
