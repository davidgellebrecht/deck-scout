#!/usr/bin/env python3
"""
Signal 8: Commercial Outdoor Seating

Only fires if the property itself IS a restaurant/cafe/bar with outdoor
seating. Does NOT fire on residential properties just because a restaurant
is nearby.
"""

from layers.base import BaseLayer


class OutdoorSeatingLayer(BaseLayer):
    name  = "outdoor_seating"
    label = "Outdoor Seating"
    paid  = False

    def run(self, prop: dict) -> dict:
        # Only fire on commercial properties that are restaurants
        prop_type = (prop.get("property_type") or "").lower()
        amenity = (prop.get("amenity") or "").lower()
        has_outdoor = prop.get("has_outdoor_seating", False)
        name = prop.get("name", "")

        # Must be a commercial/restaurant property
        if prop_type != "commercial" and amenity not in ("restaurant", "cafe", "bar"):
            return self._empty_result(
                detail="Not a restaurant — outdoor seating signal only applies to commercial properties"
            )

        if has_outdoor:
            return {
                "layer":  self.name,
                "label":  self.label,
                "signal": True,
                "score":  1.0,
                "detail": f"{name} — has outdoor seating (maintenance contract opportunity)",
                "data":   {"restaurant_name": name[:60], "has_outdoor_seating": True},
                "paid":   self.paid,
            }
        else:
            # Restaurant without outdoor seating tagged — still a potential lead
            return {
                "layer":  self.name,
                "label":  self.label,
                "signal": True,
                "score":  0.5,
                "detail": f"{name} — restaurant without confirmed outdoor seating",
                "data":   {"restaurant_name": name[:60], "has_outdoor_seating": False},
                "paid":   self.paid,
            }
