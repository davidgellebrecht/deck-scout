#!/usr/bin/env python3
"""
Signal 14: Hardscape / Drought-Resistant Conversion Candidate

San Diego homeowners with large grass lots are prime candidates for
drought-resistant hardscape conversion — which often includes adding
or expanding deck/patio areas. SD water restrictions make this common.

Uses SANDAG parcel data only — identifies large lots in areas with
water restrictions where hardscape + deck projects make sense.
"""

from layers.base import BaseLayer
import config


class HardscapeConversionLayer(BaseLayer):
    name  = "hardscape_conversion"
    label = "Hardscape Conversion"
    paid  = False

    MIN_LOT_SQFT = 5000   # Large enough lot to warrant hardscape project
    MIN_HOME_AGE = 10     # Older homes more likely to still have original lawns

    def run(self, prop: dict) -> dict:
        lot_sqft = prop.get("lot_sqft") or 0
        living_area = prop.get("living_area_sqft") or 0
        year_built = prop.get("year_built")

        if not lot_sqft or lot_sqft < self.MIN_LOT_SQFT:
            return self._empty_result(
                detail=f"Lot too small ({lot_sqft:,} sqft) for significant hardscape project"
            )

        if not year_built:
            return self._empty_result(detail="No year-built data")

        try:
            year_built = int(year_built)
        except (ValueError, TypeError):
            return self._empty_result(detail="Invalid year-built data")

        from datetime import date
        age = date.today().year - year_built
        if age < self.MIN_HOME_AGE:
            return self._empty_result(
                detail=f"Home is {age} years old — likely has modern landscaping"
            )

        # Calculate outdoor space ratio — large outdoor area = more conversion potential
        if living_area and living_area > 0:
            outdoor_ratio = (lot_sqft - living_area) / lot_sqft
        else:
            outdoor_ratio = 0.7  # assume 70% outdoor if no living area data

        if outdoor_ratio < 0.4:
            return self._empty_result(
                detail="Building footprint is too large relative to lot — limited outdoor space"
            )

        # Score by lot size and outdoor ratio
        if lot_sqft >= 10000 and outdoor_ratio >= 0.6:
            score = 1.0
            detail = f"Large lot ({lot_sqft:,} sqft, {outdoor_ratio:.0%} outdoor) — prime hardscape + deck candidate"
        elif lot_sqft >= 7000:
            score = 0.8
            detail = f"Good-sized lot ({lot_sqft:,} sqft) — strong hardscape conversion potential"
        else:
            score = 0.5
            detail = f"Moderate lot ({lot_sqft:,} sqft) — hardscape conversion possible"

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": detail,
            "data":   {
                "lot_sqft": lot_sqft,
                "outdoor_ratio": round(outdoor_ratio, 2),
                "home_age": age,
            },
            "paid":   self.paid,
        }
