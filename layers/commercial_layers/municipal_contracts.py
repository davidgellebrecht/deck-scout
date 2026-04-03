#!/usr/bin/env python3
"""
Signal 9: Municipal Boardwalk & Park Contracts

Queries SAM.gov for active/upcoming federal solicitations matching
deck, boardwalk, pier, and park maintenance keywords in San Diego County.

This signal only applies to government/municipal properties, NOT residential.
It is displayed as a standalone informational signal in the commercial section.
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
        # Only fire on non-residential properties or skip entirely
        # for residential — this is a commercial-only signal
        prop_type = (prop.get("property_type") or "").lower()
        if prop_type == "residential":
            return self._empty_result(
                detail="Municipal contracts signal — not applicable to residential properties"
            )

        if not req_lib:
            return self._empty_result(detail="requests library not available")

        # SAM.gov opportunities search
        keywords = [
            "deck maintenance",
            "boardwalk repair",
            "pier maintenance",
        ]

        all_opportunities = []
        for kw in keywords:
            try:
                params = {
                    "api_key": "",
                    "postedFrom": "01/01/2025",
                    "keyword": kw,
                    "ptype": "o",
                    "state": "CA",
                    "limit": 10,
                }
                resp = req_lib.get(
                    config.SAM_GOV_API,
                    params=params,
                    timeout=15,
                    headers={"User-Agent": "DeckScout/1.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    opps = data.get("opportunitiesData", [])
                    all_opportunities.extend(opps)
            except Exception:
                continue

        if not all_opportunities:
            return self._empty_result(
                detail="No municipal deck contracts found — check SAM.gov directly"
            )

        # Filter for San Diego County mentions
        sd_opps = []
        for opp in all_opportunities:
            title = (opp.get("title") or "").lower()
            desc = (opp.get("description") or "").lower()
            place = (opp.get("placeOfPerformance", {}).get("city", {}).get("name") or "").lower()
            if any(kw in (title + desc + place) for kw in ["san diego", "carlsbad", "oceanside", "coronado", "imperial beach"]):
                sd_opps.append(opp)

        if not sd_opps:
            return self._empty_result(detail="No San Diego County municipal contracts found")

        active = [o for o in sd_opps if (o.get("type") or "").lower() in ("o", "presolicitation")]
        score = 1.0 if active else 0.5

        sample_title = (sd_opps[0].get("title") or "Government maintenance contract")[:80]
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"{len(sd_opps)} municipal opportunity(ies) — {sample_title}",
            "data":   {
                "opportunities_found": len(sd_opps),
                "active_count": len(active),
                "sample_title": sample_title,
            },
            "paid":   self.paid,
        }
