#!/usr/bin/env python3
"""
Signal 1: New Owner Trigger

Data shows homeowners invest in exterior improvements within 6-12 months
of purchase. Checks if property sold within the last 90 days.
"""

from datetime import date, timedelta
from layers.base import BaseLayer
import config


class NewOwnerLayer(BaseLayer):
    name  = "new_owner"
    label = "New Owner"
    paid  = False

    def run(self, prop: dict) -> dict:
        sale_date_str = prop.get("sale_date")
        if not sale_date_str:
            return self._empty_result(detail="No recent sale date on record")

        try:
            if isinstance(sale_date_str, date):
                sale_date = sale_date_str
            else:
                sale_date = date.fromisoformat(str(sale_date_str)[:10])
        except (ValueError, TypeError):
            return self._empty_result(detail="Invalid sale date format")

        days_since = (date.today() - sale_date).days
        threshold = config.RECENT_SALE_DAYS

        if days_since > threshold:
            return self._empty_result(
                detail=f"Last sale {days_since} days ago — outside {threshold}-day window"
            )

        # Score decays with time since sale
        if days_since <= 30:
            score = 1.0
        elif days_since <= 60:
            score = 0.7
        else:
            score = 0.4

        # Bonus for large lots — more deck potential
        lot_sqft = prop.get("lot_sqft", 0)
        if lot_sqft and lot_sqft > 5000:
            score = self._clamp(score + 0.2)

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"Sold {days_since} days ago — prime window for deck investment",
            "data":   {
                "sale_date": str(sale_date),
                "days_since_sale": days_since,
                "lot_sqft": lot_sqft,
            },
            "paid":   self.paid,
        }
