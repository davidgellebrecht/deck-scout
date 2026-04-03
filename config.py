# ─── Deck Scout — Configuration ──────────────────────────────────────────────
# Toggle each filter True (on) or False (off).
# All enabled filters are applied as AND conditions.

FILTERS = {
    "min_property_value":       True,
    "min_lot_size":             True,
    "single_family_only":       True,
    "exclude_new_construction": True,
}

# ─── Region ──────────────────────────────────────────────────────────────────
CITY = "Imperial Beach (DEMO)"
# Bounding box: (south_lat, west_lon, north_lat, east_lon)
CITY_BBOX = (32.55, -117.14, 32.60, -117.08)

# ─── Thresholds ──────────────────────────────────────────────────────────────
MIN_PROPERTY_VALUE      = 1_500_000     # USD
MIN_LOT_SQFT            = 3_000         # square feet
NEW_CONSTRUCTION_YEARS  = 2             # exclude homes built within this many years
RECENT_SALE_DAYS        = 90            # "New Owner" trigger window
PERMIT_LOOKBACK_DAYS    = 180           # pool/spa permit recency
DECK_PERMIT_AGE_YEARS   = 10            # "Dated Deck Permit" minimum age
PERMIT_SEARCH_RADIUS_M  = 200           # proximity radius for permit signals
AGING_DECK_YEAR_MIN     = 2000          # oldest year for aging neighborhood band
AGING_DECK_YEAR_MAX     = 2013          # newest year for aging neighborhood band
CODE_ENFORCEMENT_MONTHS = 24            # look-back for safety violations
STALE_LISTING_DAYS      = 60            # "Curb Appeal" minimum days on market

# ─── Signal Toggles ─────────────────────────────────────────────────────────
SIGNALS = {
    # Residential — free
    "new_owner":            True,
    "building_permit":      True,
    "deck_permit_age":      True,
    "aging_neighborhood":   True,
    "fire_hazard":          True,
    "safety_violation":     True,
    "visual_audit":         True,
    # Commercial — free
    "outdoor_seating":      True,
    "municipal_contracts":  True,
    # Premium
    "curb_appeal":          False,
}

# ─── External API Credentials ────────────────────────────────────────────────
# Curb Appeal layer — Zillow / Redfin via RapidAPI
RAPIDAPI_KEY = ""

# ─── Data Source URLs ────────────────────────────────────────────────────────
# San Diego Open Data (Socrata) — no key required for low-volume queries
SD_OPEN_DATA_PERMITS = "https://data.sandiego.gov/resource/3hbr-gysf.json"
SD_OPEN_DATA_CODE_ENFORCEMENT = "https://data.sandiego.gov/resource/cjbr-mnhp.json"

# CAL FIRE FHSZ — bundled local GeoJSON
CALFIRE_FHSZ_GEOJSON = "data/sd_county_fhsz.geojson"

# SAM.gov — federal contract opportunities (no key required)
SAM_GOV_API = "https://api.sam.gov/opportunities/v2/search"

# ─── Overpass API (OSM) ─────────────────────────────────────────────────────
OVERPASS_FALLBACK_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
OVERPASS_TIMEOUT = 60
