#!/usr/bin/env python3
"""
app.py — Deck Scout Web Portal
West Coast Deck edition — no sidebar, city dropdown, modern professional aesthetic.

Run locally:   streamlit run app.py
Deploy:        push to GitHub → share.streamlit.io
"""

import json
import os
import time
from datetime import datetime

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import config
from scout import (
    fetch_residential_properties,
    fetch_commercial_properties,
    filter_properties,
    print_banner,
)
from rank import (
    ALL_LAYERS,
    ALL_SIGNAL_KEYS,
    SIGNAL_LABELS,
    run_all_layers,
    signals_fired_list,
)

# ── Pro access ───────────────────────────────────────────────────────────────
# Set PRO_ACCESS = "true" in Streamlit Secrets to unlock all features.
# Without it, users get a limited demo (Imperial Beach only, 3 results max).
PRO_MODE = False

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Deck Scout — West Coast Deck",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load Streamlit secrets ───────────────────────────────────────────────────
try:
    config.RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", config.RAPIDAPI_KEY)
    PRO_MODE = str(st.secrets.get("PRO_ACCESS", "")).lower() == "true"
except Exception:
    pass

DEMO_RESULT_LIMIT = 3  # Max results shown in demo mode

# ── West Coast Deck CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header            { visibility: hidden; }
.stDeployButton                      { display: none !important; }
section[data-testid="stSidebar"]     { display: none !important; }
[data-testid="collapsedControl"]     { display: none !important; }

/* ── Page background ── */
.stApp {
    background-color: #F5F5F0;
}
.main .block-container {
    padding: 3rem 5rem 4rem 5rem;
    max-width: 1100px;
    margin: 0 auto;
}

/* ── Global typography ── */
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    color: #1B2A4A;
}

/* ── Headings ── */
h1 {
    font-family: 'Poppins', sans-serif !important;
    font-weight: 700 !important;
    font-size: 2.8rem !important;
    letter-spacing: -0.02em !important;
    color: #1B2A4A !important;
    line-height: 1.1 !important;
    margin-bottom: 0.2rem !important;
}
h2, h3 {
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
    color: #1B2A4A !important;
    letter-spacing: -0.01em !important;
}

/* ── Section labels ── */
.wcd-label {
    font-family: 'Poppins', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #C0833E;
    margin-bottom: 0.15rem;
    margin-top: 0.2rem;
    display: block;
    border-bottom: 2px solid #C0833E;
    padding-bottom: 0.3rem;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid #D6D0C4 !important;
    margin: 2rem 0 !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #D6D0C4 !important;
    border-radius: 4px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.85rem !important;
    color: #1B2A4A !important;
}

/* ── Checkboxes ── */
.stCheckbox > label,
.stCheckbox > label > div,
.stCheckbox > label > span,
.stCheckbox span[data-testid="stMarkdownContainer"] p {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #1B2A4A !important;
    letter-spacing: 0.01em !important;
    opacity: 1 !important;
}

/* ── Captions ── */
.stCaption,
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.72rem !important;
    color: #5A6B7D !important;
    line-height: 1.55 !important;
    opacity: 1 !important;
}

/* ── Expander header ── */
[data-testid="stExpander"] summary p {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    color: #1B2A4A !important;
    line-height: 1.4 !important;
    opacity: 1 !important;
}
[data-testid="stExpander"] summary svg {
    color: #C0833E !important;
    fill: #C0833E !important;
}

/* ── Expander body ── */
[data-testid="stExpander"] details > div,
[data-testid="stExpander"] .streamlit-expanderContent {
    background-color: #FAFAF7 !important;
    border: 1px solid #D6D0C4 !important;
    padding: 1rem !important;
}
[data-testid="stExpander"] details > div p,
[data-testid="stExpander"] details > div span,
[data-testid="stExpander"] details > div li,
[data-testid="stExpander"] details > div strong,
[data-testid="stExpander"] details > div a,
[data-testid="stExpander"] .streamlit-expanderContent p,
[data-testid="stExpander"] .streamlit-expanderContent span,
[data-testid="stExpander"] .streamlit-expanderContent strong {
    color: #1B2A4A !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.78rem !important;
    opacity: 1 !important;
}

/* ── Primary button (Run Scan) ── */
.stButton > button[kind="primary"] {
    width: 100% !important;
    background-color: #C0833E !important;
    color: #FFFFFF !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 1rem 2rem !important;
    margin-top: 0.5rem !important;
    transition: background-color 0.2s !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #A06E2E !important;
}

/* ── Secondary buttons ── */
.stButton > button[kind="secondary"] {
    background-color: #1B2A4A !important;
    color: #FFFFFF !important;
    border: 1px solid #C0833E !important;
    border-radius: 4px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    padding: 0.7rem 1rem !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: #C0833E !important;
    border-color: #C0833E !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    background-color: transparent !important;
    color: #1B2A4A !important;
    border: 1px solid #D6D0C4 !important;
    border-radius: 4px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}
.stDownloadButton > button:hover {
    border-color: #1B2A4A !important;
    background-color: #1B2A4A !important;
    color: #FFFFFF !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #D6D0C4;
    border-radius: 4px;
    padding: 1.1rem 1.3rem;
}
[data-testid="metric-container"] label {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.58rem !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: #C0833E !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Poppins', sans-serif !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #1B2A4A !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #D6D0C4;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.62rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    padding: 0.8rem 1.6rem !important;
    background: transparent !important;
    border: none !important;
    color: #C0833E !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    border-bottom: 2px solid #1B2A4A !important;
    color: #1B2A4A !important;
}

/* ── Info / status box ── */
.stInfo {
    background-color: #ECEAE4 !important;
    border: 1px solid #D6D0C4 !important;
    border-radius: 4px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.8rem !important;
    color: #1B2A4A !important;
}

/* ── Success boxes ── */
[data-testid="stAlert"][data-baseweb="notification"]:has(svg[data-testid="stAlertDynamicIcon-success"]),
.stSuccess, [data-testid="stAlert"].stSuccess {
    background-color: #E8F5E9 !important;
    border: 1.5px solid #2E7D32 !important;
    border-radius: 4px !important;
    opacity: 1 !important;
}
.stSuccess p, .stSuccess div, .stSuccess span {
    color: #1B5E20 !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    opacity: 1 !important;
}

/* ── Warning box ── */
.stWarning, [data-testid="stAlert"].stWarning,
[data-testid="stAlert"]:has([data-testid="stAlertDynamicIcon-warning"]) {
    background-color: #FFF9E6 !important;
    border: 1px solid #C0833E !important;
    border-radius: 4px !important;
    opacity: 1 !important;
}
.stWarning p, .stWarning li, .stWarning strong,
.stWarning span, .stWarning code, .stWarning div {
    color: #1B2A4A !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.78rem !important;
    opacity: 1 !important;
}

/* ── Demo button ── */
[data-testid="column"]:has(.demo-marker) button {
    background-color: #B71C1C !important;
    color: #FFFFFF !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 4px !important;
    width: 100% !important;
    padding: 0.9rem 1rem !important;
    animation: demo-pulse 2.5s ease-in-out infinite;
}
[data-testid="column"]:has(.demo-marker) button:hover {
    background-color: #7F0000 !important;
}
@keyframes demo-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(183,28,28,0.5); }
    50%       { box-shadow: 0 0 0 6px rgba(183,28,28,0); }
}

/* ── Images ── */
[data-testid="stImage"] {
    padding: 0 !important;
    margin: 0 !important;
}

/* ── Dataframe ── */
.stDataFrame { border: 1px solid #D6D0C4 !important; border-radius: 4px !important; }

/* ── Status widget ── */
[data-testid="stStatusWidget"] {
    background-color: #1B2A4A !important;
    border-radius: 4px !important;
}
[data-testid="stStatusWidget"] p,
[data-testid="stStatusWidget"] span,
[data-testid="stStatusWidget"] div {
    color: #FFFFFF !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.78rem !important;
    opacity: 1 !important;
}
[data-testid="stStatusWidget"] > div:last-child {
    background-color: #FAFAF7 !important;
    border: 1px solid #D6D0C4 !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stStatusWidget"] > div:last-child p,
[data-testid="stStatusWidget"] > div:last-child span {
    color: #1B2A4A !important;
    font-size: 0.75rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Upgrade CTA ──────────────────────────────────────────────────────────────

def show_upgrade_cta():
    """Display the upgrade prompt for demo users."""
    st.markdown(
        '<div style="background:linear-gradient(135deg, #1B2A4A 0%, #2C3E50 100%);'
        'border:2px solid #C0833E;border-radius:8px;padding:2rem 2.5rem;'
        'margin:1.5rem 0;text-align:center;">'
        '<div style="font-size:1.4rem;margin-bottom:0.5rem;">&#128274;</div>'
        '<div style="font-family:Poppins,sans-serif;font-size:1.1rem;font-weight:700;'
        'color:#FFFFFF;margin-bottom:0.6rem;">Upgrade to Deck Scout Pro</div>'
        '<div style="font-family:Poppins,sans-serif;font-size:0.78rem;color:#D6D0C4;'
        'line-height:1.6;max-width:500px;margin:0 auto;">'
        'Unlock all 28 San Diego County cities, unlimited property results, '
        'CSV/JSON export, and all 10 signal layers.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── San Diego County cities ──────────────────────────────────────────────────
SAN_DIEGO_CITIES = {
    "Imperial Beach (DEMO)": {"zips": ["91932"], "bbox": (32.55, -117.14, 32.60, -117.08)},
    "Carlsbad":              {"zips": ["92008","92009","92010","92011"], "bbox": (33.07, -117.38, 33.21, -117.24)},
    "Chula Vista":           {"zips": ["91910","91911","91913","91914","91915"], "bbox": (32.58, -117.10, 32.68, -116.94)},
    "Coronado":              {"zips": ["92118"], "bbox": (32.66, -117.19, 32.71, -117.13)},
    "Del Mar":               {"zips": ["92014"], "bbox": (32.94, -117.28, 32.97, -117.24)},
    "El Cajon":              {"zips": ["92019","92020","92021"], "bbox": (32.76, -117.00, 32.83, -116.88)},
    "Encinitas":             {"zips": ["92023","92024"], "bbox": (33.01, -117.31, 33.09, -117.24)},
    "Escondido":             {"zips": ["92025","92026","92027","92029"], "bbox": (33.08, -117.13, 33.17, -116.99)},
    "La Mesa":               {"zips": ["91941","91942"], "bbox": (32.74, -117.04, 32.79, -116.98)},
    "Lemon Grove":           {"zips": ["91945"], "bbox": (32.72, -117.04, 32.75, -117.00)},
    "National City":         {"zips": ["91950"], "bbox": (32.65, -117.11, 32.69, -117.07)},
    "Oceanside":             {"zips": ["92054","92056","92057","92058"], "bbox": (33.15, -117.40, 33.25, -117.24)},
    "Poway":                 {"zips": ["92064"], "bbox": (32.93, -117.07, 33.02, -116.94)},
    "San Diego":             {"zips": ["92101"], "bbox": (32.53, -117.28, 33.11, -116.90)},
    "San Marcos":            {"zips": ["92069","92078"], "bbox": (33.11, -117.22, 33.17, -117.12)},
    "Santee":                {"zips": ["92071"], "bbox": (32.82, -117.00, 32.88, -116.93)},
    "Solana Beach":          {"zips": ["92075"], "bbox": (32.98, -117.28, 33.01, -117.24)},
    "Vista":                 {"zips": ["92081","92083","92084"], "bbox": (33.17, -117.27, 33.23, -117.18)},
    # Unincorporated communities
    "Alpine":                {"zips": ["91901"], "bbox": (32.80, -116.80, 32.86, -116.73)},
    "Bonita":                {"zips": ["91902"], "bbox": (32.65, -117.05, 32.68, -116.99)},
    "Fallbrook":             {"zips": ["92028"], "bbox": (33.34, -117.28, 33.40, -117.20)},
    "Jamul":                 {"zips": ["91935"], "bbox": (32.70, -116.88, 32.73, -116.82)},
    "Lakeside":              {"zips": ["92040"], "bbox": (32.84, -116.95, 32.88, -116.88)},
    "Ramona":                {"zips": ["92065"], "bbox": (33.03, -116.90, 33.07, -116.83)},
    "Rancho San Diego":      {"zips": ["92019"], "bbox": (32.74, -116.95, 32.78, -116.89)},
    "Rancho Santa Fe":       {"zips": ["92067"], "bbox": (33.00, -117.22, 33.05, -117.17)},
    "Spring Valley":         {"zips": ["91977","91978"], "bbox": (32.72, -117.00, 32.76, -116.94)},
    "Valley Center":         {"zips": ["92082"], "bbox": (33.20, -117.05, 33.25, -116.97)},
}

# ── Signal metadata ──────────────────────────────────────────────────────────
SIGNAL_META = [
    {
        "key":    "layer_new_owner_signal",
        "label":  "New Owner",
        "group":  "residential",
        "config": "new_owner",
        "paid":   False,
        "desc":   "Homes sold in the last 90 days. Data shows homeowners invest in major exterior improvements within 6-12 months of buying a home.",
    },
    {
        "key":    "layer_building_permit_signal",
        "label":  "Pool/Spa Permit",
        "group":  "residential",
        "config": "building_permit",
        "paid":   False,
        "desc":   "Recent pool, spa, or outdoor kitchen permits nearby. A pool almost always requires a surrounding deck or patio — the owner is already in 'construction mode' with financing secured.",
    },
    {
        "key":    "layer_deck_permit_age_signal",
        "label":  "Dated Deck Permit",
        "group":  "residential",
        "config": "deck_permit_age",
        "paid":   False,
        "desc":   "Deck, patio, or balcony permits issued 10+ years ago. A 15-year-old deck likely needs replacement or major repair.",
    },
    {
        "key":    "layer_aging_neighborhood_signal",
        "label":  "Aging Deck",
        "group":  "residential",
        "config": "aging_neighborhood",
        "paid":   False,
        "desc":   "Homes built 2000-2013 — original decks are hitting their replacement cycle. Pressure-treated wood decks become unsafe after 15-20 years.",
    },
    {
        "key":    "layer_fire_hazard_signal",
        "label":  "Fire Hazard Zone",
        "group":  "residential",
        "config": "fire_hazard",
        "paid":   False,
        "desc":   "Properties in CAL FIRE high-risk zones. Insurance companies are dropping homeowners unless they harden homes against fire. Non-combustible decking (composite/aluminum) is often required to keep coverage.",
    },
    {
        "key":    "layer_safety_violation_signal",
        "label":  "Safety Violation",
        "group":  "residential",
        "config": "safety_violation",
        "paid":   False,
        "desc":   "Properties flagged for unsafe structures, deck/balcony/stair violations in city Code Enforcement logs. These owners need a solution provider to clear city fines — you're not selling, you're solving.",
    },
    {
        "key":    "layer_visual_audit_signal",
        "label":  "Visual Audit (OSM)",
        "group":  "residential",
        "config": "visual_audit",
        "paid":   False,
        "desc":   "Queries OpenStreetMap for building material tags (wood, timber), deck/patio features, and construction dates. Free alternative to Street View AI — detects properties with likely aging wood decks.",
    },
    {
        "key":    "layer_sb326_compliance_signal",
        "label":  "SB-326 Compliance",
        "group":  "residential",
        "config": "sb326_compliance",
        "paid":   False,
        "desc":   "California SB-326 (condos/HOAs) and SB-721 (apartments) require balcony/deck inspections for all multi-family buildings. First deadline was Jan 1, 2025 — already passed. Non-compliant buildings face legal liability. A single condo complex contract = $50K-200K+.",
    },
    {
        "key":    "layer_neighbor_effect_signal",
        "label":  "Neighbor Effect",
        "group":  "residential",
        "config": "neighbor_effect",
        "paid":   False,
        "desc":   "When one house on a street gets a new deck, neighbors follow within 12-18 months. Detects recent deck permits on nearby properties — social proof that deck improvements are happening in the area.",
    },
    {
        "key":    "layer_flip_activity_signal",
        "label":  "Flip Activity",
        "group":  "residential",
        "config": "flip_activity",
        "paid":   False,
        "desc":   "Properties bought recently (≤180 days) with old year-built (15+ years) are likely being flipped. Flippers always invest in outdoor improvements and work on tight timelines — receptive to deck proposals.",
    },
    {
        "key":    "layer_hardscape_conversion_signal",
        "label":  "Hardscape Conversion",
        "group":  "residential",
        "config": "hardscape_conversion",
        "paid":   False,
        "desc":   "Homeowners converting lawns to drought-resistant hardscape often add or expand deck/patio areas at the same time. San Diego's water restrictions make this increasingly common.",
    },
    {
        "key":    "layer_outdoor_seating_signal",
        "label":  "Outdoor Seating",
        "group":  "commercial",
        "config": "outdoor_seating",
        "paid":   False,
        "desc":   "Restaurants and cafes with outdoor decks/seating areas. Post-pandemic, thousands added permanent outdoor decks. High-traffic = high wear = recurring quarterly maintenance contracts with higher liability motivation.",
    },
    {
        "key":    "layer_municipal_contracts_signal",
        "label":  "Municipal Contracts",
        "group":  "commercial",
        "config": "municipal_contracts",
        "paid":   False,
        "desc":   "Active/upcoming government solicitations on SAM.gov for boardwalk, pier, and park deck maintenance. One government contract can pay overhead for an entire crew for a year.",
    },
    {
        "key":    "layer_curb_appeal_signal",
        "label":  "Curb Appeal",
        "group":  "premium",
        "config": "curb_appeal",
        "paid":   True,
        "desc":   "Homes listed 60+ days (stale listings). Sellers are desperate — if photos show a gray, weathered deck, pitch the listing agent a 'Weekend Refresh' package (power wash + stain) to help close the sale.",
    },
]

FILTER_META = [
    {
        "key":   "min_property_value",
        "label": "Min Property Value ($1.5M+)",
        "desc":  "Excludes properties assessed below $1,500,000 — focuses on premium homeowners with budget for quality deck work.",
    },
    {
        "key":   "min_lot_size",
        "label": "Min Lot Size (3,000+ sqft)",
        "desc":  "Excludes small lots under 3,000 sqft — ensures enough yard space for a meaningful deck project.",
    },
    {
        "key":   "exclude_new_construction",
        "label": "Exclude New Construction",
        "desc":  "Excludes homes built within the last 2 years — new homes already have modern decking.",
    },
]

# Property type is handled separately as a selectbox (not a checkbox)
PROPERTY_TYPE_OPTIONS = {
    "All":         "Show all property types — residential, condos, apartments, and commercial.",
    "Residential": "Houses, condos, townhomes, and apartments — any property where people live.",
    "Commercial":  "Restaurants, bars, cafes, and other businesses with outdoor deck areas.",
}

PREMIUM_LAYER_INFO = {
    "curb_appeal": {
        "api":       "Zillow / Redfin via RapidAPI",
        "cost":      "Free tier: 500 requests/month; paid plans above that",
        "free_tier": "500 requests/month free at RapidAPI",
        "setup":     "Register at rapidapi.com → subscribe to a Zillow API → set RAPIDAPI_KEY in Streamlit Secrets (or config.py for local use).",
        "degrades":  False,
    },
}

LAYER_CRED = {
    "curb_appeal": "RAPIDAPI_KEY",
}


# ── Score helpers ────────────────────────────────────────────────────────────

def _signal_config_key(signal_key: str) -> str:
    """Extract the config key from a signal key like 'layer_new_owner_signal' -> 'new_owner'."""
    return signal_key.replace("layer_", "").replace("_signal", "")


def rescore(properties: list, active_keys: list) -> list:
    """Weighted scoring using signal weights * layer confidence scores + seasonal boost."""
    from datetime import datetime
    month = datetime.now().month
    seasonal = config.SEASONAL_MULTIPLIERS.get(month, 1.0)

    max_possible = sum(
        config.SIGNAL_WEIGHTS.get(_signal_config_key(k), 1.0)
        for k in active_keys
    )

    result = []
    for p in properties:
        p = dict(p)
        weighted_sum = 0.0
        fired_count = 0
        for k in active_keys:
            if p.get(k):
                fired_count += 1
                cfg_key = _signal_config_key(k)
                weight = config.SIGNAL_WEIGHTS.get(cfg_key, 1.0)
                # Use the layer's confidence score (0-1) as a multiplier
                score_key = k.replace("_signal", "_score")
                layer_score = p.get(score_key)
                confidence = float(layer_score) if layer_score is not None else 1.0
                # Apply seasonal multiplier (exempt for compliance signals)
                mult = 1.0 if cfg_key in config.SEASONAL_EXEMPT_SIGNALS else seasonal
                weighted_sum += weight * confidence * mult

        raw_score = round((weighted_sum / max_possible) * 100, 1) if max_possible else 0.0
        p["opportunity_score"] = min(raw_score, 100.0)
        p["signals_fired"]     = fired_count
        p["signals_total"]     = len(active_keys)
        # Lead tier
        if p["opportunity_score"] >= 40:
            p["lead_tier"] = "Hot"
        elif p["opportunity_score"] >= 20:
            p["lead_tier"] = "Warm"
        else:
            p["lead_tier"] = "Cold"
        result.append(p)
    return sorted(result, key=lambda x: x["opportunity_score"], reverse=True)


def score_color(score: float) -> str:
    if score >= 40:
        return "#B71C1C"  # red for hot leads
    if score >= 20:
        return "#C0833E"  # amber for warm
    return "#7A8A9D"      # grey for cold


def lead_tier_badge(tier: str) -> str:
    """Return HTML badge for lead tier."""
    colors = {
        "Hot":  ("🔥", "#B71C1C", "#FFEBEE"),
        "Warm": ("☀️", "#C0833E", "#FFF8E1"),
        "Cold": ("❄️", "#7A8A9D", "#ECEFF1"),
    }
    icon, text_color, bg_color = colors.get(tier, colors["Cold"])
    return (
        f'<span style="display:inline-block;background:{bg_color};color:{text_color};'
        f'font-family:Poppins,sans-serif;font-size:0.6rem;font-weight:700;'
        f'padding:2px 8px;border-radius:3px;letter-spacing:0.08em;'
        f'text-transform:uppercase;">{icon} {tier} Lead</span>'
    )


def estimate_deck_size(p: dict) -> tuple:
    """Estimate deck size range and project value from lot and living area."""
    lot = p.get("lot_sqft") or 0
    living = p.get("living_area_sqft") or 0
    if not lot or lot < 500:
        return None, None, None, None

    available = max(lot - living - config.DRIVEWAY_ESTIMATE_SQFT, 0)
    if p.get("has_pool"):
        available = max(available - 400, 0)  # pool takes space but boosts deck need

    low_sqft = max(int(available * config.DECK_RATIO_LOW), 80)
    high_sqft = max(int(available * config.DECK_RATIO_HIGH), 150)

    # Cap at reasonable sizes
    low_sqft = min(low_sqft, 800)
    high_sqft = min(high_sqft, 1500)

    low_val = low_sqft * config.DECK_COST_PER_SQFT_LOW
    high_val = high_sqft * config.DECK_COST_PER_SQFT_HIGH

    return low_sqft, high_sqft, low_val, high_val


# ── Pipeline runner ──────────────────────────────────────────────────────────

def run_full_scan(filter_state: dict, signal_state: dict) -> list:
    for k, v in filter_state.items():
        config.FILTERS[k] = v
    for k, v in signal_state.items():
        config.SIGNALS[k] = v

    # Check for demo cached data
    if config.CITY == "Imperial Beach (DEMO)":
        demo_path = "demo_data/imperial_beach_demo.json"
        if os.path.exists(demo_path):
            st.session_state.scan_log.append("Loading cached demo data...")
            with open(demo_path, "r") as f:
                properties = json.load(f)
            st.session_state.total_raw = len(properties)
            st.session_state.scan_log.append(f"  -> {len(properties)} demo properties loaded")
            return properties

    # Fetch residential parcels from SanGIS/SANDAG
    st.session_state.scan_log.append("Querying SanGIS/SANDAG for residential parcels...")
    properties = fetch_residential_properties()
    st.session_state.scan_log.append(f"  -> {len(properties):,} parcels retrieved from SANDAG")

    # Fetch commercial properties (restaurants with outdoor seating) from OSM
    prop_type_filter = filter_state.get("property_type", "All")
    if prop_type_filter in ("All", "Commercial"):
        st.session_state.scan_log.append("Querying OpenStreetMap for restaurants with outdoor seating...")
        commercial = fetch_commercial_properties()
        properties.extend(commercial)
        st.session_state.scan_log.append(f"  -> {len(commercial)} restaurant(s) found in OSM")

    st.session_state.total_raw = len(properties)

    st.session_state.scan_log.append("Applying hard filters...")
    properties, skipped = filter_properties(properties)
    st.session_state.scan_log.append(
        f"  -> {len(properties)} passed  |  "
        f"value: {skipped['property_value']}  |  "
        f"lot: {skipped['lot_size']}  |  "
        f"type: {skipped['property_type']}  |  "
        f"new: {skipped['new_construction']}"
    )

    if not properties:
        return []

    st.session_state.scan_log.append("Running signal layers...")
    properties = run_all_layers(properties)
    st.session_state.scan_log.append("  -> All layers complete")

    return properties


# ── Map builder ──────────────────────────────────────────────────────────────

def build_map(properties: list) -> folium.Map:
    if not properties:
        return folium.Map(location=[32.7, -117.1], zoom_start=11)

    lats   = [p["lat"] for p in properties]
    lons   = [p["lon"] for p in properties]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]
    m      = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")

    for p in properties:
        score   = p.get("opportunity_score", 0)
        color   = "#2E7D32" if score >= 30 else "#C0833E" if score >= 15 else "#9CA3AF"
        address = p.get("address", "")
        signals = signals_fired_list(p)
        sig_html = "".join(
            f'<span style="background:#E8F5E9;color:#1B5E20;padding:2px 6px;'
            f'border:1px solid #2E7D32;font-size:10px;margin:2px;display:inline-block;'
            f'border-radius:3px;">{s}</span>'
            for s in signals
        ) or "<em style='color:#7A8A9D'>no signals</em>"

        year = p.get("year_built", "")
        year_str = f"Built {year}" if year else "Year unknown"

        popup_html = f"""
        <div style="font-family:'Poppins',sans-serif;min-width:230px;color:#1B2A4A;
                    background:#F5F5F0;padding:14px;border:1px solid #D6D0C4;border-radius:4px;">
          <div style="font-size:22px;font-weight:700;color:{color};">{score:.1f}
            <span style="font-size:12px;color:#7A8A9D;">/100</span>
          </div>
          <div style="font-size:12px;font-weight:500;margin:4px 0 8px;">{address[:50]}</div>
          <div style="font-size:10px;color:#7A8A9D;margin-bottom:6px;">
            {year_str} &nbsp;·&nbsp; {p.get('building_type','residential').title()}
          </div>
          <div style="margin-top:8px;">{sig_html}</div>
        </div>
        """
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=8 + score / 10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{score:.1f}/100 — {address[:35]}",
        ).add_to(m)

    return m


# ── Rankings table builder ───────────────────────────────────────────────────

def build_rankings_df(properties: list) -> pd.DataFrame:
    rows = []
    for rank, p in enumerate(properties, 1):
        fired = signals_fired_list(p)
        rows.append({
            "Rank":       rank,
            "Score":      p.get("opportunity_score", 0),
            "Signals":    f"{p.get('signals_fired',0)}/{p.get('signals_total', len(ALL_SIGNAL_KEYS))}",
            "Fired":      " · ".join(fired) if fired else "—",
            "Address":    p.get("address", ""),
            "Year Built": p.get("year_built", ""),
            "Type":       p.get("building_type", "").title(),
            "GPS":        p.get("gps_coordinates", ""),
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

# ── Header ───────────────────────────────────────────────────────────────────
_logo_col, _title_col = st.columns([1, 3])
with _logo_col:
    if os.path.exists("assets/wcd_logo.png"):
        st.image("assets/wcd_logo.png", width=160)
with _title_col:
    st.markdown("# Deck Scout")
    st.markdown("*West Coast Deck — BD Opportunity Intelligence — San Diego County*")

st.markdown("---")

# ── City selector ────────────────────────────────────────────────────────────
st.markdown('<span class="wcd-label">Target Area</span>', unsafe_allow_html=True)

if PRO_MODE:
    st.caption("Select a city in San Diego County to scan for deck opportunities.")
    city_names = list(SAN_DIEGO_CITIES.keys())
else:
    st.caption("Demo mode — Imperial Beach only. Upgrade to Pro to unlock all 28 cities.")
    city_names = ["Imperial Beach (DEMO)"]

default_idx = 0

selected_city = st.selectbox(
    "City",
    options=city_names,
    index=default_idx,
    label_visibility="collapsed",
    key="city_select",
)

if not PRO_MODE and selected_city != "Imperial Beach (DEMO)":
    selected_city = "Imperial Beach (DEMO)"

config.CITY      = selected_city
config.CITY_BBOX = SAN_DIEGO_CITIES[selected_city]["bbox"]

if not PRO_MODE:
    # Show locked cities as a visual teaser
    locked_cities = [c for c in SAN_DIEGO_CITIES.keys() if c != "Imperial Beach (DEMO)"]
    locked_html = "".join(
        f'<span style="display:inline-block;background:#ECEAE4;color:#7A8A9D;'
        f'font-family:Poppins,sans-serif;font-size:0.65rem;padding:3px 8px;'
        f'margin:2px;border:1px solid #D6D0C4;border-radius:3px;">'
        f'&#128274; {c}</span>'
        for c in locked_cities[:12]
    )
    remaining = len(locked_cities) - 12
    if remaining > 0:
        locked_html += (
            f'<span style="display:inline-block;color:#7A8A9D;font-family:Poppins,sans-serif;'
            f'font-size:0.65rem;padding:3px 8px;margin:2px;">+ {remaining} more</span>'
        )
    st.markdown(
        f'<div style="margin:0.3rem 0 0.5rem;">{locked_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Hard Filters ─────────────────────────────────────────────────────────────
st.markdown('<span class="wcd-label">Hard Filters</span>', unsafe_allow_html=True)
st.caption("All enabled filters must pass — failing any one excludes the property.")

fc1, fc2 = st.columns(2)
filter_state = {}
for i, fm in enumerate(FILTER_META):
    col = fc1 if i % 2 == 0 else fc2
    with col:
        filter_state[fm["key"]] = st.checkbox(
            fm["label"],
            value=config.FILTERS[fm["key"]],
            key=f"filter_{fm['key']}",
        )
        st.caption(fm["desc"])

# Property type selector
st.markdown("")
prop_type_options = list(PROPERTY_TYPE_OPTIONS.keys())
selected_prop_type = st.selectbox(
    "Property Type",
    options=prop_type_options,
    index=0,
    key="filter_property_type",
)
st.caption(PROPERTY_TYPE_OPTIONS[selected_prop_type])
filter_state["property_type"] = selected_prop_type

st.markdown("---")

# ── Residential Signals ──────────────────────────────────────────────────────
st.markdown('<span class="wcd-label">Residential Signals</span>', unsafe_allow_html=True)
st.caption("All free — annotation only, never excludes properties. Toggle to adjust the Opportunity Score.")

signal_state = {}
residential_signals = [sm for sm in SIGNAL_META if sm["group"] == "residential"]

sc1, sc2, sc3 = st.columns(3)
for i, sm in enumerate(residential_signals):
    col = [sc1, sc2, sc3][i % 3]
    with col:
        signal_state[sm["config"]] = st.checkbox(
            sm["label"],
            value=config.SIGNALS.get(sm["config"], True),
            key=f"sig_{sm['key']}",
        )
        st.caption(sm["desc"])

st.markdown("---")

# ── Commercial Signals ───────────────────────────────────────────────────────
st.markdown('<span class="wcd-label">Commercial Signals</span>', unsafe_allow_html=True)
st.caption("Free — targets businesses and government contracts for recurring deck maintenance revenue.")

commercial_signals = [sm for sm in SIGNAL_META if sm["group"] == "commercial"]

cc1, cc2 = st.columns(2)
for i, sm in enumerate(commercial_signals):
    col = [cc1, cc2][i % 2]
    with col:
        signal_state[sm["config"]] = st.checkbox(
            sm["label"],
            value=config.SIGNALS.get(sm["config"], True),
            key=f"sig_{sm['key']}",
        )
        st.caption(sm["desc"])

st.markdown("---")

# ── Premium Layers ───────────────────────────────────────────────────────────
st.markdown('<span class="wcd-label">Premium Layers</span>', unsafe_allow_html=True)
st.caption("Require API credentials — disabled by default. Enable when credentials are configured.")

premium_signals = [sm for sm in SIGNAL_META if sm["group"] == "premium"]

for sm in premium_signals:
    info = PREMIUM_LAYER_INFO.get(sm["config"], {})
    signal_state[sm["config"]] = st.checkbox(
        sm["label"],
        value=False,
        key=f"sig_{sm['key']}",
    )
    st.caption(sm["desc"])
    if info:
        with st.expander("Setup & pricing"):
            st.markdown(f"**API source:** {info['api']}")
            st.markdown(f"**Cost:** {info['cost']}")
            if info.get("free_tier"):
                st.markdown(f"**Free tier:** {info['free_tier']}")
            else:
                st.markdown("**Free tier:** None")
            st.markdown(
                f"**Without credentials:** "
                f"{'Returns limited data' if info['degrades'] else 'Returns no data — layer contributes nothing to the score'}"
            )
            st.markdown(f"**Setup:** {info['setup']}")

# ── Credential warning ───────────────────────────────────────────────────────
missing_creds = []
for cfg_key, cred_var in LAYER_CRED.items():
    if signal_state.get(cfg_key) and not getattr(config, cred_var, ""):
        info = PREMIUM_LAYER_INFO[cfg_key]
        label = next(sm["label"] for sm in SIGNAL_META if sm["config"] == cfg_key)
        missing_creds.append((label, cred_var, info))

if missing_creds:
    n = len(missing_creds)
    rows_html = ""
    for label, cred_var, info in missing_creds:
        rows_html += (
            f'<li style="margin-bottom:0.5rem;">'
            f'<strong>{label}</strong>'
            f' — needs <code style="background:#FFF0A0;padding:1px 4px;border-radius:3px;'
            f'color:#8B4513;font-size:0.72rem;">{cred_var}</code>'
            f'<br><span style="color:#5A6B7D;font-size:0.72rem;">-> {info["setup"]}</span>'
            f'</li>'
        )
    st.markdown(
        f'<div style="background:#FFF9C4;border:1.5px solid #C0833E;padding:1rem 1.2rem;'
        f'border-radius:4px;margin:0.5rem 0;">'
        f'<p style="color:#1B2A4A;font-weight:700;margin:0 0 0.4rem 0;font-family:Poppins,sans-serif;'
        f'font-size:0.82rem;">'
        f'{n} premium layer{"s" if n > 1 else ""} enabled without credentials.</p>'
        f'<ul style="color:#1B2A4A;font-family:Poppins,sans-serif;font-size:0.78rem;'
        f'margin:0;padding-left:1.2rem;">{rows_html}</ul></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Run Scan button ──────────────────────────────────────────────────────────
if st.session_state.get("scan_time"):
    elapsed = st.session_state.get("scan_elapsed", 0)
    st.caption(
        f"Last scan: {st.session_state.scan_time.strftime('%Y-%m-%d  %H:%M')}  "
        f"({elapsed:.0f}s)  ·  City: {st.session_state.get('scan_city', '')}"
    )

run_btn = st.button("Run Deck Scout Scan", type="primary", use_container_width=True)

# ── Trigger scan ─────────────────────────────────────────────────────────────
if run_btn:
    st.session_state.scan_log  = []
    st.session_state.scan_city = config.CITY
    t0 = time.time()

    with st.status("Running Deck Scout scan...", expanded=True) as scan_status:
        log_placeholder = st.empty()

        import builtins
        original_print = builtins.print

        def ui_print(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            st.session_state.scan_log.append(msg)
            log_placeholder.markdown(
                "\n".join(f"> {line}" for line in st.session_state.scan_log[-8:])
            )
            original_print(*args, **kwargs)

        builtins.print = ui_print
        try:
            properties = run_full_scan(filter_state, signal_state)
        finally:
            builtins.print = original_print

        elapsed = time.time() - t0
        st.session_state.properties   = properties
        st.session_state.scan_time    = datetime.now()
        st.session_state.scan_elapsed = elapsed

        total_raw = st.session_state.get("total_raw", 0)
        if properties:
            scan_status.update(
                label=(
                    f"Scan complete — scanned {total_raw:,} properties in {config.CITY}, "
                    f"found {len(properties)} results  ({elapsed:.0f}s)"
                ),
                state="complete",
            )
        else:
            scan_status.update(
                label=f"Scan complete — scanned {total_raw:,} properties, none passed all hard filters",
                state="error",
            )

# ── Display results ──────────────────────────────────────────────────────────
st.markdown("---")

if "properties" not in st.session_state or not st.session_state.properties:
    if not st.session_state.get("properties"):
        st.markdown(
            '<div style="background:#ECEAE4;border:1px solid #D6D0C4;'
            'border-radius:4px;padding:1rem 1.2rem;">'
            '<p style="color:#1B2A4A;font-family:Poppins,sans-serif;'
            'font-size:0.82rem;margin:0 0 0.3rem 0;">'
            'Configure your parameters above and click <strong>Run Deck Scout Scan</strong> to begin.</p>'
            '<p style="color:#5A6B7D;font-family:Poppins,sans-serif;'
            'font-size:0.78rem;margin:0;">'
            'The scan queries OpenStreetMap and public data sources for deck opportunities in your selected city.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning("No properties passed all hard filters. Try relaxing some filters above.")
else:
    # Determine active signal keys from current toggle state
    active_keys = [
        sm["key"]
        for sm in SIGNAL_META
        if signal_state.get(sm["config"], True)
    ]

    # Re-score instantly from cached signals
    properties = rescore(st.session_state.properties, active_keys)

    # ── Summary metrics ──────────────────────────────────────────────────────
    scores    = [p["opportunity_score"] for p in properties]
    total_raw = st.session_state.get("total_raw", 0)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Properties Matched", len(properties), help=f"{total_raw:,} total properties scanned")
    n_active = len(active_keys)
    m2.metric("Top Score", f"{max(scores):.0f}%", help=f"Percentage of active signals fired ({n_active} signals running)")
    m3.metric("Average Score", f"{sum(scores)/len(scores):.0f}%")
    m4.metric("Signals Active", f"{n_active} of {len(ALL_SIGNAL_KEYS)}", help="Enable more signals to deepen the analysis")
    if total_raw:
        st.caption(
            f"Scanned **{total_raw:,}** total properties in {st.session_state.get('scan_city', config.CITY)}"
            f" — **{len(properties)}** matched all required filters."
        )

    st.markdown("---")

    # ── Export buttons ────────────────────────────────────────────────────────
    if PRO_MODE:
        df_full   = build_rankings_df(properties)
        csv_data  = df_full.to_csv(index=False).encode("utf-8")
        json_data = json.dumps(properties, indent=2, default=str).encode("utf-8")
        ts        = datetime.now().strftime("%Y%m%d_%H%M")

        # Build mailing list CSV
        mail_rows = []
        for p in properties:
            addr = p.get("address", "")
            # Parse address components
            parts = addr.split(",")
            street = parts[0].strip() if parts else ""
            city_zip = parts[1].strip() if len(parts) > 1 else ""
            city_parts = city_zip.split()
            zipcode = city_parts[-1] if city_parts and city_parts[-1].isdigit() else ""
            city_name = " ".join(city_parts[:-1]) if zipcode else city_zip
            mail_rows.append({
                "Name": "Current Resident",
                "Address": street,
                "City": city_name,
                "State": "CA",
                "ZIP": zipcode,
                "Lead Tier": p.get("lead_tier", ""),
                "Score": p.get("opportunity_score", 0),
                "Top Signal": (signals_fired_list(p) or ["—"])[0],
            })
        mail_csv = pd.DataFrame(mail_rows).to_csv(index=False).encode("utf-8")

        ec1, ec2, ec3, _ = st.columns([1, 1, 1, 3])
        ec1.download_button(
            "Export CSV",
            csv_data,
            file_name=f"deck_scout_{ts}.csv",
            mime="text/csv",
        )
        ec2.download_button(
            "Export JSON",
            json_data,
            file_name=f"deck_scout_{ts}.json",
            mime="application/json",
        )
        ec3.download_button(
            "Mailing List",
            mail_csv,
            file_name=f"deck_scout_mailing_{ts}.csv",
            mime="text/csv",
        )
    else:
        st.markdown(
            '<div style="background:#ECEAE4;border:1px solid #D6D0C4;border-radius:4px;'
            'padding:0.6rem 1rem;font-family:Poppins,sans-serif;font-size:0.75rem;color:#7A8A9D;">'
            '&#128274; CSV and JSON export available with Deck Scout Pro.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_rank, tab_map, tab_raw = st.tabs(["Rankings", "Map", "Raw Data"])

    # ── Property Cards ───────────────────────────────────────────────────────
    with tab_rank:
        active_report = st.session_state.get("active_report", None)

        def render_report(idx, p):
            """Render the full-width Intelligence Report panel."""
            score     = p["opportunity_score"]
            address   = p.get("address", f"Property #{idx+1}")
            fired     = signals_fired_list(p)
            score_clr = score_color(score)

            st.markdown(
                f'<div style="margin:0.8rem 0 1rem;padding:1.2rem 1.4rem;'
                f'background:#ECEAE4;border:1px solid #D6D0C4;border-top:3px solid #C0833E;'
                f'border-radius:4px;">'
                f'<div style="font-family:Poppins,sans-serif;font-size:0.56rem;font-weight:700;'
                f'letter-spacing:0.2em;text-transform:uppercase;color:#C0833E;">Opportunity Report</div>'
                f'<div style="font-family:Poppins,sans-serif;font-size:1.6rem;font-weight:700;'
                f'color:#1B2A4A;line-height:1.2;margin-top:0.15rem;">{address}</div>'
                f'<div style="font-family:Poppins,sans-serif;font-size:0.68rem;color:{score_clr};'
                f'font-weight:600;margin-top:0.25rem;">'
                f'Opportunity Score: {score:.0f}% ({p.get("signals_fired",0)} of {p.get("signals_total", n_active)} signals)'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            dc1, dc2, dc3 = st.columns(3)
            dc1.metric("Opportunity Score", f"{score:.0f}%")
            dc1.metric("Year Built", p.get("year_built") or "Unknown")
            dc2.metric("Building Type", (p.get("building_type") or "residential").title())
            dc2.metric("Material", (p.get("material") or "Unknown").title())
            dc3.metric("Property Type", (p.get("property_type") or "residential").title())
            dc3.metric("GPS", p.get("gps_coordinates", ""))

            st.markdown("**Signals fired:**")
            if fired:
                sig_cols = st.columns(min(len(fired), 4))
                for i, sig in enumerate(fired):
                    sig_cols[i % 4].success(f"  {sig}")
            else:
                st.caption("No signals fired for this property.")

            unfired = [sm["label"] for sm in SIGNAL_META if sm["key"] in active_keys and not p.get(sm["key"])]
            if unfired:
                st.markdown("**Not triggered:**")
                st.caption("  ·  ".join(unfired))

            with st.expander("Full signal details"):
                detail_rows = []
                for sm in SIGNAL_META:
                    if sm["key"] not in active_keys:
                        continue
                    detail_key = sm["key"].replace("_signal", "_detail")
                    detail_rows.append({
                        "Signal": sm["label"],
                        "Fired":  "Yes" if p.get(sm["key"]) else "—",
                        "Detail": str(p.get(detail_key, "")),
                    })
                st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

        # Render cards in rows of 3 (limited in demo mode)
        row_size = 3
        display_properties = properties if PRO_MODE else properties[:DEMO_RESULT_LIMIT]
        for row_start in range(0, len(display_properties), row_size):
            row_props = display_properties[row_start:row_start + row_size]
            cols = st.columns(row_size)

            for col_idx, (col, p) in enumerate(zip(cols, row_props)):
                idx       = row_start + col_idx
                score     = p["opportunity_score"]
                address   = p.get("address", f"Property #{idx+1}")
                fired     = signals_fired_list(p)
                year      = p.get("year_built", "")
                btype     = (p.get("building_type") or "residential").title()
                score_clr = score_color(score)
                is_open   = (active_report == idx)

                with col:
                    # Map link placeholder
                    lat = p.get("lat", 32.7)
                    lon = p.get("lon", -117.1)
                    maps_url = f"https://www.google.com/maps/@{lat},{lon},18z"
                    st.markdown(
                        f'<a href="{maps_url}" target="_blank" style="text-decoration:none;">'
                        f'<div style="width:100%;height:120px;background:#ECEAE4;margin-bottom:0;'
                        f'display:flex;flex-direction:column;align-items:center;justify-content:center;'
                        f'border:1px solid #D6D0C4;border-radius:4px;cursor:pointer;">'
                        f'<div style="font-size:1.4rem;margin-bottom:0.3rem;">📍</div>'
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.6rem;font-weight:600;'
                        f'letter-spacing:0.08em;color:#5A6B7D;margin-bottom:0.2rem;">'
                        f'{lat:.4f}, {lon:.4f}</div>'
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.52rem;color:#C0833E;">'
                        f'View on Google Maps</div>'
                        f'</div></a>',
                        unsafe_allow_html=True,
                    )
                    tier = p.get("lead_tier", "Cold")
                    tier_html = lead_tier_badge(tier)
                    st.markdown(
                        f'<div style="padding:0.6rem 0 0.4rem;border-bottom:1px solid #D6D0C4;">'
                        f'{tier_html}'
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.56rem;font-weight:700;'
                        f'letter-spacing:0.14em;text-transform:uppercase;color:{score_clr};margin:0.3rem 0 0.15rem;">'
                        f'Score {score:.0f}% ({p.get("signals_fired",0)} of {p.get("signals_total", n_active)})</div>'
                        f'<div style="font-family:Poppins,sans-serif;font-weight:600;font-size:0.9rem;'
                        f'color:#1B2A4A;line-height:1.25;">{address[:55]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    # Key Intel table — expanded with all available fields
                    year_str = str(year) if year else "—"
                    lot_str = f"{p.get('lot_sqft'):,} sqft" if p.get("lot_sqft") else "—"
                    val_str = f"${p.get('assessed_value'):,}" if p.get("assessed_value") else "—"
                    bed_bath = ""
                    beds = str(p.get("bedrooms", "")).strip().lstrip("0")
                    baths_val = str(p.get("baths", "")).strip().lstrip("0")
                    if beds or baths_val:
                        bed_bath = f"{beds or '—'} bed / {baths_val or '—'} bath"
                    else:
                        bed_bath = "—"
                    pool_str = "Yes" if p.get("has_pool") else "No"

                    # Deck size estimate
                    deck_lo, deck_hi, val_lo, val_hi = estimate_deck_size(p)
                    if deck_lo and deck_hi:
                        deck_str = f"{deck_lo:,}-{deck_hi:,} sqft"
                        proj_str = f"${val_lo:,}-${val_hi:,}"
                    else:
                        deck_str = "—"
                        proj_str = "—"

                    td_l = 'style="padding:2px 4px;color:#7A8A9D;"'
                    td_r = 'style="padding:2px 0;text-align:right;font-weight:500;"'
                    st.markdown(
                        f'<div style="padding:0.5rem 0;border-bottom:1px solid #D6D0C4;">'
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.52rem;font-weight:700;'
                        f'letter-spacing:0.16em;text-transform:uppercase;color:#C0833E;margin-bottom:0.3rem;">Key Intel</div>'
                        f'<table style="width:100%;border-collapse:collapse;font-family:Poppins,sans-serif;'
                        f'font-size:0.72rem;color:#1B2A4A;">'
                        f'<tr><td {td_l}>Year Built</td><td {td_r}>{year_str}</td></tr>'
                        f'<tr><td {td_l}>Lot Size</td><td {td_r}>{lot_str}</td></tr>'
                        f'<tr><td {td_l}>Assessed</td><td {td_r}>{val_str}</td></tr>'
                        f'<tr><td {td_l}>Bed / Bath</td><td {td_r}>{bed_bath}</td></tr>'
                        f'<tr><td {td_l}>Pool</td><td {td_r}>{pool_str}</td></tr>'
                        f'<tr><td {td_l}>Est. Deck</td><td {td_r}>{deck_str}</td></tr>'
                        f'<tr><td {td_l}>Project Value</td><td {td_r}>{proj_str}</td></tr>'
                        f'</table></div>',
                        unsafe_allow_html=True,
                    )
                    if fired:
                        chips = "".join(
                            f'<span style="display:inline-block;background:#E8F5E9;color:#1B5E20;'
                            f'border:1px solid #2E7D32;font-family:Poppins,sans-serif;'
                            f'font-size:0.58rem;padding:2px 6px;margin:2px 2px 0 0;'
                            f'border-radius:3px;">{sig}</span>'
                            for sig in fired
                        )
                        st.markdown(f'<div style="padding:0.4rem 0 0.5rem;">{chips}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '<div style="padding:0.4rem 0 0.5rem;font-family:Poppins,sans-serif;'
                            'font-size:0.7rem;color:#7A8A9D;font-style:italic;">No signals fired</div>',
                            unsafe_allow_html=True,
                        )
                    btn_label = "Close Report" if is_open else "View Report"
                    if st.button(btn_label, key=f"report_btn_{idx}", use_container_width=True):
                        st.session_state.active_report = None if is_open else idx
                        st.rerun()

            # After each row: inject report if this row contains the active card
            if active_report is not None and row_start <= active_report < row_start + row_size:
                render_report(active_report, properties[active_report])

        # Show upgrade CTA if results were truncated
        if not PRO_MODE and len(properties) > DEMO_RESULT_LIMIT:
            remaining = len(properties) - DEMO_RESULT_LIMIT
            st.markdown(
                f'<div style="text-align:center;padding:0.8rem 0;font-family:Poppins,sans-serif;'
                f'font-size:0.75rem;color:#7A8A9D;margin-bottom:0.5rem;">'
                f'+ {remaining} more propert{"y" if remaining == 1 else "ies"} hidden in demo mode</div>',
                unsafe_allow_html=True,
            )
            show_upgrade_cta()

    # ── Map ──────────────────────────────────────────────────────────────────
    with tab_map:
        st.caption(
            "Pins sized and coloured by Opportunity Score.  "
            "Green >= 30  ·  Gold 15-29  ·  Grey < 15.  Click any pin for details."
        )
        map_properties = properties if PRO_MODE else properties[:DEMO_RESULT_LIMIT]
        m = build_map(map_properties)
        st_folium(m, use_container_width=True, height=560)
        if not PRO_MODE and len(properties) > DEMO_RESULT_LIMIT:
            show_upgrade_cta()

    # ── Raw Data ─────────────────────────────────────────────────────────────
    with tab_raw:
        if PRO_MODE:
            st.caption("Complete field dump for all properties, sorted by Opportunity Score.")
            raw_properties = properties
        else:
            st.caption("Demo mode — showing first 3 results only.")
            raw_properties = properties[:DEMO_RESULT_LIMIT]
        all_keys = list(dict.fromkeys(k for p in raw_properties for k in p.keys()))
        df_raw = pd.DataFrame([
            {k: str(p.get(k, "")) if p.get(k) is not None else "" for k in all_keys}
            for p in raw_properties
        ])
        st.dataframe(df_raw, use_container_width=True, height=500)
        if not PRO_MODE and len(properties) > DEMO_RESULT_LIMIT:
            show_upgrade_cta()

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
_fc1, _fc2, _fc3 = st.columns([2, 1, 2])
with _fc2:
    if os.path.exists("assets/wcd_logo.png"):
        st.image("assets/wcd_logo.png", width=100)
st.markdown(
    '<p style="font-family:Poppins,sans-serif;font-size:0.8rem;'
    'color:#7A8A9D;text-align:center;letter-spacing:0.04em;">'
    'West Coast Deck &nbsp;·&nbsp; Deck Scout &nbsp;·&nbsp; San Diego County Deck Opportunity Intelligence'
    '</p>',
    unsafe_allow_html=True,
)
