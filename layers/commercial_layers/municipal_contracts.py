#!/usr/bin/env python3
"""
Signal 9: Municipal Boardwalk & Park Contracts

Queries SAM.gov for active/upcoming federal solicitations matching
deck, boardwalk, pier, and park maintenance keywords in San Diego County.
One government deck contract can pay overhead for an entire crew for a year.
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
        if not req_lib:
            return self._empty_result(detail="requests library not available")

        # SAM.gov opportunities search
        keywords = [
            "deck maintenance",
            "boardwalk repair",
            "pier maintenance",
            "park deck",
            "overlook maintenance",
            "railing repair",
        ]

        all_opportunities = []
        for kw in keywords[:3]:  # Limit to avoid rate limits
            try:
                params = {
                    "api_key": "",  # SAM.gov public search doesn't require a key for basic queries
                    "postedFrom": "01/01/2025",
                    "keyword": kw,
                    "ptype": "o",  # opportunities
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
            # SAM.gov may require an API key for full access —
            # return a helpful message rather than failing silently
            return self._empty_result(
                detail="No municipal deck contracts found — check SAM.gov directly for local opportunities"
            )

        # Filter for San Diego County mentions
        sd_opps = []
        for opp in all_opportunities:
            title = (opp.get("title") or "").lower()
            desc = (opp.get("description") or "").lower()
            place = (opp.get("placeOfPerformance", {}).get("city", {}).get("name") or "").lower()
            if any(kw in (title + desc + place) for kw in ["san diego", "carlsbad", "oceanside", "coronado"]):
                sd_opps.append(opp)

        if not sd_opps:
            sd_opps = all_opportunities[:3]  # Show top results even if not SD-specific

        active = [o for o in sd_opps if (o.get("type") or "").lower() in ("o", "presolicitation")]
        score = 1.0 if active else 0.5

        sample_title = (sd_opps[0].get("title") or "Government maintenance contract")[:80]
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": True,
            "score":  score,
            "detail": f"{len(sd_opps)} municipal opportunity(ies) found — {sample_title}",
            "data":   {
                "opportunities_found": len(sd_opps),
                "active_count": len(active),
                "sample_title": sample_title,
            },
            "paid":   self.paid,
        }
