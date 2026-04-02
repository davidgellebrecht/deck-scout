#!/usr/bin/env python3
"""
rank.py — Signal Registry, Scoring Engine & Layer Pipeline

Runs all 10 Deck Scout signal layers against properties and computes
an equal-weighted Opportunity Score.

SIGNAL INVENTORY — 10 signals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Residential (7):
  layer_new_owner_signal            Recent home purchase (≤90 days)
  layer_building_permit_signal      Pool/spa permit nearby
  layer_deck_permit_age_signal      Deck permit 10+ years old
  layer_aging_neighborhood_signal   Home built 2000-2013
  layer_fire_hazard_signal          CAL FIRE FHSZ zone
  layer_safety_violation_signal     Code enforcement violation
  layer_visual_audit_signal         OSM building material tags

Commercial (2):
  layer_outdoor_seating_signal      Restaurant outdoor seating
  layer_municipal_contracts_signal  Government deck contracts

Premium (1):
  layer_curb_appeal_signal          Stale listing (60+ days)
"""

import csv
import json
import sys
from datetime import datetime

import config

# ── Import all 10 layer classes ──────────────────────────────────────────────
from layers.property_layers.new_owner          import NewOwnerLayer
from layers.property_layers.building_permit    import BuildingPermitLayer
from layers.property_layers.deck_permit_age    import DeckPermitAgeLayer
from layers.property_layers.aging_neighborhood import AgingNeighborhoodLayer
from layers.risk_layers.fire_hazard            import FireHazardLayer
from layers.risk_layers.safety_violation       import SafetyViolationLayer
from layers.risk_layers.visual_audit           import VisualAuditLayer
from layers.commercial_layers.outdoor_seating  import OutdoorSeatingLayer
from layers.commercial_layers.municipal_contracts import MunicipalContractsLayer
from layers.premium_layers.curb_appeal         import CurbAppealLayer

# ── Layer registry ───────────────────────────────────────────────────────────
# Execution order: instant/free → API-calling free → paid last
ALL_LAYERS = [
    # Tier 0: Free, no external API, instant
    AgingNeighborhoodLayer(),
    # Tier 1: Free, local data (bundled GeoJSON)
    FireHazardLayer(),
    # Tier 2: Free, queries public data APIs
    NewOwnerLayer(),
    BuildingPermitLayer(),
    DeckPermitAgeLayer(),
    SafetyViolationLayer(),
    # Tier 3: Free, OSM queries
    VisualAuditLayer(),
    OutdoorSeatingLayer(),
    MunicipalContractsLayer(),
    # Tier 4: Premium, paid APIs
    CurbAppealLayer(),
]

# ── All 10 signal keys ──────────────────────────────────────────────────────
ALL_SIGNAL_KEYS = [
    "layer_new_owner_signal",
    "layer_building_permit_signal",
    "layer_deck_permit_age_signal",
    "layer_aging_neighborhood_signal",
    "layer_fire_hazard_signal",
    "layer_safety_violation_signal",
    "layer_visual_audit_signal",
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
    "Outdoor Seating",
    "Muni Contract",
    "Curb Appeal",
]


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_property(prop: dict) -> float:
    """Equal-weighted Opportunity Score: each signal worth 100/N points."""
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
    """Run all layers against every property and attach result fields."""
    enabled = [l for l in ALL_LAYERS if config.SIGNALS.get(l.name, True)]
    total = len(properties)

    for i, prop in enumerate(properties, 1):
        for layer in enabled:
            result = layer.run(prop)
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
