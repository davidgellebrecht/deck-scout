#!/usr/bin/env python3
"""
Signal 13: Flip/Renovation Activity

Properties bought recently with old year_built are likely being flipped.
Flippers always invest in outdoor improvements — they're receptive to
deck proposals and work on tight timelines.

Data: FREE — uses existing SANDAG sale_date + year_built data.
Zero new API calls.
"""

from datetime import date
from layers.base import BaseLayer


class FlipActivityLayer(BaseLayer):
    name  = "flip_activity"
    label = "Flip Activity"
    paid  = False

    FLIP_WINDOW_DAYS = 180  # purchased within last 6 months
    MIN_HOME_AGE = 15       # home must be at least this old to be a flip candidate

    def run(self, prop: dict) -> dict:
        sale_date_raw = prop.get("sale_date")
        year_built = prop.get("year_built")

        if not sale_date_raw:
            return self._empty_result(detail="No recent sale date — cannot assess flip activity")

        if not year_built:
            return self._empty_result(detail="No year-built data — cannot assess flip potential")

        try:
            if isinstance(sale_date_raw, date):
                sale_date = sale_date_raw
            else:
                sale_date = date.fromisoformat(str(sale_date_raw)[:10])
        except (ValueError, TypeError):
            return self._empty_result(detail="Invalid sale date")

        days_since = (date.today() - sale_date).days
        current_year = date.today().year
        home_age = current_year - int(year_built)

        # Must be recently purchased AND old enough to need renovation
        if days_since > self.FLIP_WINDOW_DAYS:
            return self._empty_result(
                detail=f"Last sale {days_since} days ago — outside {self.FLIP_WINDOW_DAYS}-day flip window"
            )

        if home_age < self.MIN_HOME_AGE:
            return self._empty_result(
                detail=f"Home is {home_age} years old — too new for typical flip renovation"
            )

        # Score by combination of recency and age
        if days_since <= 90 and home_age >= 25:
            score = 1.0
            detail = f"Likely flip — bought {days_since}d ago, {home_age} yr old home"
        elif days_since <= 90:
            score = 0.8
            detail = f"Possible flip — bought {days_since}d ago, {home_age} yr old home"
        elif home_age >= 25:
            score = 0.7
            detail = f"Renovation candidate — bought {days_since}d ago, {home_age} yr old home"
        else:
            score = 0.5
            detail = f"Recent purchase of older home — {days_since}d ago, {home_age} yrs old"

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "days_since_purchase": days_since,
                "home_age_years": home_age,
            },
            "paid":   self.paid,
        }
