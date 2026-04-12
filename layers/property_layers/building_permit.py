#!/usr/bin/env python3
"""
Signal 2: Pool/Spa on Property

Properties with pools almost always need a surrounding deck or patio.
Uses the SANDAG parcel data `pool` field (Y/N) directly — no external
API call needed. More accurate than distance-based permit matching.

If a property has a pool AND was recently purchased, the owner is
especially likely to invest in deck construction.
"""

from datetime import date
from layers.base import BaseLayer
import config


class BuildingPermitLayer(BaseLayer):
    name  = "building_permit"
    label = "Pool/Spa Permit"
    paid  = False

    def run(self, prop: dict) -> dict:
        has_pool = prop.get("has_pool", False)

        if not has_pool:
            return self._empty_result(detail="No pool on this parcel")

        # Pool confirmed on the parcel — strong deck opportunity
        score = 0.8

        # Boost if recently purchased (new owner + pool = high intent)
        sale_date_raw = prop.get("sale_date")
        if sale_date_raw:
            try:
                if isinstance(sale_date_raw, date):
                    sale_date = sale_date_raw
                else:
                    sale_date = date.fromisoformat(str(sale_date_raw)[:10])
                days_since = (date.today() - sale_date).days
                if days_since <= config.RECENT_SALE_DAYS:
                    score = 1.0
            except (ValueError, TypeError):
                pass

        lot_sqft = prop.get("lot_sqft", 0)
        detail = "Pool on parcel — deck/patio surround opportunity"
        if score == 1.0:
            detail = "Pool + recent purchase — high-intent deck opportunity"

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "has_pool": True,
                "lot_sqft": lot_sqft,
            },
            "paid":   self.paid,
        }
