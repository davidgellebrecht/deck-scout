#!/usr/bin/env python3
"""
Signal 11: SB-326 / SB-721 Balcony Inspection Compliance

California law requires ALL multi-family buildings (3+ units) to have
balconies, decks, and exterior elevated elements inspected:
  - SB-326 (condos/HOAs): First deadline Jan 1, 2025 — already passed
  - SB-721 (apartments): Inspections every 6 years

Every non-compliant building is in violation NOW. A single condo complex
contract can be worth $50K-200K+.

Data: FREE — uses existing SANDAG parcel data. Land use codes already
distinguish condos (120), duplexes (140-141), and apartments (150-159).
Zero new API calls.
"""

from datetime import date
from layers.base import BaseLayer


# Multi-family land use codes from SANDAG
SB326_USE_CODES = {120}             # Condos — SB-326
SB721_USE_CODES = {140, 141, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159}  # Apartments/duplexes — SB-721


class SB326ComplianceLayer(BaseLayer):
    name  = "sb326_compliance"
    label = "SB-326 Compliance"
    paid  = False

    def run(self, prop: dict) -> dict:
        use_code = 0
        try:
            use_code = int(str(prop.get("land_use_code", "0")).strip())
        except (ValueError, TypeError):
            pass

        # Only applies to multi-family (condos, duplexes, apartments)
        is_sb326 = use_code in SB326_USE_CODES
        is_sb721 = use_code in SB721_USE_CODES

        if not is_sb326 and not is_sb721:
            return self._empty_result(
                detail="Not a multi-family building — SB-326/721 does not apply"
            )

        year_built = prop.get("year_built")
        current_year = date.today().year

        # Determine law and urgency
        if is_sb326:
            law = "SB-326"
            detail_prefix = "Condo/HOA"
            deadline = "Jan 1, 2025 (PASSED)"
        else:
            law = "SB-721"
            detail_prefix = "Multi-family"
            deadline = "every 6 years"

        # Score by building age — older = more likely wood rot and structural issues
        if year_built and year_built < 2000:
            score = 1.0
            age_note = f"built {year_built} ({current_year - year_built} yrs) — high risk of wood rot"
        elif year_built and year_built < 2010:
            score = 0.8
            age_note = f"built {year_built} ({current_year - year_built} yrs) — inspection likely overdue"
        elif year_built and year_built < 2020:
            score = 0.5
            age_note = f"built {year_built} ({current_year - year_built} yrs) — inspection required"
        else:
            score = 0.3
            age_note = "recent construction — inspection still mandated"

        building_type = prop.get("building_type", "multi-family")
        units = str(prop.get("bedrooms", "")).strip()

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"{detail_prefix} — {law} inspection required (deadline: {deadline}), {age_note}",
            "data":   {
                "applicable_law": law,
                "deadline": deadline,
                "building_type": building_type,
                "land_use_code": use_code,
            },
            "paid":   self.paid,
        }
