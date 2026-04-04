#!/usr/bin/env python3
"""
rank.py — Signal Registry, Scoring Engine & Layer Pipeline

Runs all 14 Deck Scout signal layers against properties and computes
a weighted Opportunity Score.

SIGNAL INVENTORY — 14 signals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Residential (11):
  layer_new_owner_signal            Recent home purchase (≤90 days)
  layer_building_permit_signal      Pool/spa permit on same parcel
  layer_deck_permit_age_signal      Deck permit 10+ years old
  layer_aging_neighborhood_signal   Home built 2000-2013
  layer_fire_hazard_signal          CAL FIRE FHSZ zone
  layer_safety_violation_signal     Code enforcement violation
  layer_visual_audit_signal         OSM building material tags
  layer_sb326_compliance_signal     SB-326/721 balcony inspection mandate
  layer_neighbor_effect_signal      Nearby recent deck permits
  layer_flip_activity_signal        Likely house flip in progress
  layer_hardscape_conversion_signal Lawn-to-hardscape conversion

Commercial (2):
  layer_outdoor_seating_signal      Restaurant outdoor seating
  layer_municipal_contracts_signal  Government deck contracts

Premium (1):
  layer_curb_appeal_signal          Stale listing (60+ days)
"""

import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import config

# ── Import all 14 layer classes ──────────────────────────────────────────────
from layers.property_layers.new_owner           import NewOwnerLayer
from layers.property_layers.building_permit     import BuildingPermitLayer
from layers.property_layers.deck_permit_age     import DeckPermitAgeLayer
from layers.property_layers.aging_neighborhood  import AgingNeighborhoodLayer
from layers.property_layers.sb326_compliance    import SB326ComplianceLayer
from layers.property_layers.neighbor_effect     import NeighborEffectLayer
from layers.property_layers.flip_activity       import FlipActivityLayer
from layers.property_layers.hardscape_conversion import HardscapeConversionLayer
from layers.risk_layers.fire_hazard             import FireHazardLayer
from layers.risk_layers.safety_violation        import SafetyViolationLayer
from layers.risk_layers.visual_audit            import VisualAuditLayer
from layers.commercial_layers.outdoor_seating   import OutdoorSeatingLayer
from layers.commercial_layers.municipal_contracts import MunicipalContractsLayer
from layers.premium_layers.curb_appeal          import CurbAppealLayer

# ── Layer registry ───────────────────────────────────────────────────────────
ALL_LAYERS = [
    # Tier 0: Free, no external API, instant
    AgingNeighborhoodLayer(),
    SB326ComplianceLayer(),
    FlipActivityLayer(),
    # Tier 1: Free, local data (bundled GeoJSON)
    FireHazardLayer(),
    # Tier 2: Free, uses data already in property dict
    NewOwnerLayer(),
    # Tier 3: Free, queries public data APIs (Socrata)
    BuildingPermitLayer(),
    DeckPermitAgeLayer(),
    SafetyViolationLayer(),
    NeighborEffectLayer(),
    HardscapeConversionLayer(),
    # Tier 4: Free, OSM queries
    VisualAuditLayer(),
    OutdoorSeatingLayer(),
    MunicipalContractsLayer(),
    # Tier 5: Premium, paid APIs
    CurbAppealLayer(),
]

# ── All 14 signal keys ──────────────────────────────────────────────────────
ALL_SIGNAL_KEYS = [
    "layer_new_owner_signal",
    "layer_building_permit_signal",
    "layer_deck_permit_age_signal",
    "layer_aging_neighborhood_signal",
    "layer_fire_hazard_signal",
    "layer_safety_violation_signal",
    "layer_visual_audit_signal",
    "layer_sb326_compliance_signal",
    "layer_neighbor_effect_signal",
    "layer_flip_activity_signal",
    "layer_hardscape_conversion_signal",
    "layer_outdoor_seating_signal",
    "layer_municipal_contracts_signal",
    "layer_curb_appeal_signal",
]

SIGNAL_LABELS = [
    "New Owner",
    "Pool Permit",
    "Dated Deck",
    "Aging Deck",
    "Fire Zone",
    "Safety Viol.",
    "Visual Audit",
    "SB-326",
    "Neighbor",
    "Flip Activity",
    "Hardscape",
    "Outdoor Seating",
    "Muni Contract",
    "Curb Appeal",
]


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_property(prop: dict) -> float:
    """Weighted Opportunity Score using signal weights and confidence."""
    fired = sum(1 for key in ALL_SIGNAL_KEYS if prop.get(key))
    return round((fired / len(ALL_SIGNAL_KEYS)) * 100, 1)


def signals_fired_list(prop: dict) -> list:
    """Return the short labels of every signal that fired."""
    return [
        label for key, label in zip(ALL_SIGNAL_KEYS, SIGNAL_LABELS)
        if prop.get(key)
    ]


# ─── Layer annotation ────────────────────────────────────────────────────────

def run_all_layers(properties: list) -> list:
    """
    Run all layers against every property in parallel.
    Uses ThreadPoolExecutor for 3-5x speedup since most layers
    make independent HTTP requests.
    """
    enabled = [l for l in ALL_LAYERS if config.SIGNALS.get(l.name, True)]
    total = len(properties)
    max_workers = min(len(enabled), 8)

    for i, prop in enumerate(properties, 1):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_layer = {
                executor.submit(layer.run, prop): layer
                for layer in enabled
            }
            for future in as_completed(future_to_layer):
                layer = future_to_layer[future]
                try:
                    result = future.result(timeout=60)
                except Exception as exc:
                    result = layer._empty_result(
                        detail=f"Layer error: {str(exc)[:80]}"
                    )
                prefix = f"layer_{result['layer']}"
                prop[f"{prefix}_signal"] = result["signal"]
                prop[f"{prefix}_score"]  = result["score"]
                prop[f"{prefix}_detail"] = result["detail"]
                prop[f"{prefix}_paid"]   = result["paid"]
                for k, v in result.get("data", {}).items():
                    prop[f"{prefix}_{k}"] = v

        if i % 5 == 0 or i == total:
            sys.stdout.write(f"\r  Running layers... {i}/{total} properties")
            sys.stdout.flush()

    print()
    return properties


# ─── Output ──────────────────────────────────────────────────────────────────

def export_csv(properties: list, path: str):
    if not properties:
        return
    all_keys = list(dict.fromkeys(k for p in properties for k in p.keys()))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, restval="")
        writer.writeheader()
        writer.writerows(properties)


def export_json(properties: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(properties, f, indent=2, ensure_ascii=False, default=str)
