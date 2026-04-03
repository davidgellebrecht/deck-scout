#!/usr/bin/env python3
"""
Signal 9: Municipal Boardwalk & Park Contracts

Searches SAM.gov for active/upcoming federal solicitations matching
deck, boardwalk, pier, and park maintenance keywords in San Diego County.

This signal only applies to government/municipal properties, NOT residential.
Uses the SAM.gov public search (no API key required for basic queries).
"""

from layers.base import BaseLayer
import config

try:
    import requests as req_lib
except ImportError:
    req_lib = None


class MunicipalContractsLayer(BaseLayer):
    name  = "municipal_contracts"
    label = "Municipal Contracts"
    paid  = False

    def run(self, prop: dict) -> dict:
        # Only fire on non-residential properties
        prop_type = (prop.get("property_type") or "").lower()
        if prop_type == "residential":
            return self._empty_result(
                detail="Municipal contracts signal — not applicable to residential properties"
            )

        if not req_lib:
            return self._empty_result(detail="requests library not available")

        # SAM.gov public opportunities search
        # The public API endpoint allows basic searches without an API key
        keywords = ["deck maintenance", "boardwalk repair", "pier maintenance"]

        all_opportunities = []
        for kw in keywords:
            try:
                # Use SAM.gov public search endpoint
                params = {
                    "keyword": kw,
                    "postedFrom": "01/01/2025",
                    "ptype": "o",
                    "state": "CA",
                    "limit": 10,
                }
                resp = req_lib.get(
                    "https://sam.gov/api/prod/opportunities/v1/search",
                    params=params,
                    timeout=15,
                    headers={"User-Agent": "DeckScout/1.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Handle different response formats
                    opps = (
                        data.get("opportunitiesData", [])
                        or data.get("_embedded", {}).get("results", [])
                        or data.get("opportunities", [])
                    )
                    if isinstance(opps, list):
                        all_opportunities.extend(opps)
            except Exception:
                continue

        if not all_opportunities:
            return self._empty_result(
                detail="No municipal deck contracts found on SAM.gov"
            )

        # Filter for San Diego area
        sd_keywords = ["san diego", "carlsbad", "oceanside", "coronado",
                       "imperial beach", "chula vista", "encinitas", "del mar"]
        sd_opps = []
        for opp in all_opportunities:
            title = str(opp.get("title") or opp.get("name") or "").lower()
            desc = str(opp.get("description") or "").lower()
            combined = title + " " + desc
            if any(kw in combined for kw in sd_keywords):
                sd_opps.append(opp)

        if not sd_opps:
            return self._empty_result(
                detail=f"Found {len(all_opportunities)} CA contract(s) but none in San Diego County"
            )

        sample_title = str(
            sd_opps[0].get("title") or sd_opps[0].get("name") or "Government contract"
        )[:80]

        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  1.0,
            "detail": f"{len(sd_opps)} municipal opportunity(ies) — {sample_title}",
            "data":   {
                "opportunities_found": len(sd_opps),
                "sample_title": sample_title,
            },
            "paid":   self.paid,
        }
