#!/usr/bin/env python3
"""
Signal 6: Safety Violation Risk

Identifies properties at high risk for deck/balcony safety violations
based on building age, type, and material. Older multi-story wood-frame
buildings with decks/balconies are the most likely to have safety issues.

Previously queried the SD Code Enforcement Socrata API, but that endpoint
is no longer available (404). This version uses property characteristics
as a proxy for violation risk.
"""

from datetime import date
from layers.base import BaseLayer


class SafetyViolationLayer(BaseLayer):
    name  = "safety_violation"
    label = "Safety Violation"
    paid  = False

    def run(self, prop: dict) -> dict:
        year_built = prop.get("year_built")
        if not year_built:
            return self._empty_result(detail="No year-built data — cannot assess violation risk")

        try:
            year_built = int(year_built)
        except (ValueError, TypeError):
            return self._empty_result(detail="Invalid year-built data")

        current_year = date.today().year
        age = current_year - year_built

        # Risk factors for deck/balcony safety violations
        risk_score = 0.0
        risk_factors = []

        # Age is the primary factor — wood rot accelerates after 20 years
        if age >= 30:
            risk_score += 0.5
            risk_factors.append(f"{age} yrs old (high rot risk)")
        elif age >= 20:
            risk_score += 0.3
            risk_factors.append(f"{age} yrs old (moderate rot risk)")
        elif age >= 15:
            risk_score += 0.1
            risk_factors.append(f"{age} yrs old")
        else:
            return self._empty_result(
                detail=f"Home is {age} years old — low violation risk"
            )

        # Multi-story buildings have elevated decks/balconies — higher safety stakes
        levels = prop.get("building_levels") or prop.get("building:levels", "")
        if levels:
            try:
                if int(str(levels).strip()) >= 2:
                    risk_score += 0.2
                    risk_factors.append("multi-story (elevated deck risk)")
            except (ValueError, TypeError):
                pass

        # Building type — duplexes and multi-family have shared structures
        btype = (prop.get("building_type") or "").lower()
        if btype in ("duplex", "apartments"):
            risk_score += 0.2
            risk_factors.append(f"{btype} (shared structural elements)")

        # Wood material confirmed
        material = (prop.get("material") or "").lower()
        if "wood" in material or "timber" in material:
            risk_score += 0.1
            risk_factors.append("wood construction")

        if risk_score < 0.3:
            return self._empty_result(
                detail=f"Low violation risk profile — {', '.join(risk_factors) or 'insufficient risk factors'}"
            )

        score = self._clamp(risk_score)
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"Elevated violation risk — {', '.join(risk_factors)}",
            "data":   {
                "risk_score": round(score, 2),
                "risk_factors": risk_factors,
                "home_age": age,
            },
            "paid":   self.paid,
        }
