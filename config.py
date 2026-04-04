# ─── Deck Scout — Configuration ──────────────────────────────────────────────
# Toggle each filter True (on) or False (off).
# All enabled filters are applied as AND conditions.

FILTERS = {
    "min_property_value":       True,
    "min_lot_size":             True,
    "exclude_new_construction": True,
    "property_type":            "All",    # "All", "Residential", or "Commercial"
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
PERMIT_SEARCH_RADIUS_M  = 30            # same-parcel only (GPS drift tolerance)
AGING_DECK_YEAR_MIN     = 2000          # oldest year for aging neighborhood band
AGING_DECK_YEAR_MAX     = 2013          # newest year for aging neighborhood band
CODE_ENFORCEMENT_MONTHS = 24            # look-back for safety violations
STALE_LISTING_DAYS      = 60            # "Curb Appeal" minimum days on market

# ─── Signal Toggles ─────────────────────────────────────────────────────────
SIGNALS = {
    # Residential — free
    "new_owner":              True,
    "building_permit":        True,
    "deck_permit_age":        True,
    "aging_neighborhood":     True,
    "fire_hazard":            True,
    "safety_violation":       True,
    "visual_audit":           True,
    "sb326_compliance":       True,
    "neighbor_effect":        True,
    "flip_activity":          True,
    "hardscape_conversion":   True,
    # Commercial — free
    "outdoor_seating":        True,
    "municipal_contracts":    True,
    # Premium
    "curb_appeal":            False,
}

# ─── Signal Weights (for weighted scoring) ──────────────────────────────────
# Higher weight = stronger buying signal. Used with each layer's 0-1 confidence
# score to produce a weighted opportunity score.
SIGNAL_WEIGHTS = {
    "safety_violation":     3.0,   # owner MUST act — city fines accumulating
    "sb326_compliance":     3.0,   # legal mandate — inspection deadline passed
    "fire_hazard":          2.5,   # insurance mandate for non-combustible decking
    "new_owner":            2.0,   # strongest purchase-intent signal
    "building_permit":      2.0,   # already in construction mode
    "municipal_contracts":  2.0,   # high-value government work
    "flip_activity":        2.0,   # flipper on tight timeline, receptive to bids
    "deck_permit_age":      1.5,   # aging deck confirmed by permit records
    "curb_appeal":          1.5,   # stale listing — motivated seller
    "outdoor_seating":      1.5,   # recurring commercial revenue
    "neighbor_effect":      1.5,   # social proof — neighbors got new decks
    "hardscape_conversion": 1.5,   # already doing outdoor work
    "aging_neighborhood":   1.0,   # statistical — not individually confirmed
    "visual_audit":         1.0,   # OSM data is sparse in US suburbs
}

# ─── Seasonal Multiplier ────────────────────────────────────────────────────
# Homeowners plan deck projects in spring. Compliance signals are year-round.
SEASONAL_MULTIPLIERS = {
    1: 1.20, 2: 1.20, 3: 1.20,    # Jan-Mar: planning season
    4: 1.00, 5: 1.00, 6: 1.00,    # Apr-Jun: peak season
    7: 0.90, 8: 0.90, 9: 0.90,    # Jul-Sep: winding down
    10: 0.85, 11: 0.85, 12: 0.85, # Oct-Dec: off season
}
# These signals are exempt from seasonal reduction (compliance is year-round):
SEASONAL_EXEMPT_SIGNALS = {"safety_violation", "fire_hazard"}

# ─── Deck Size Estimation ───────────────────────────────────────────────────
DECK_COST_PER_SQFT_LOW  = 35    # composite decking low estimate ($/sqft)
DECK_COST_PER_SQFT_HIGH = 55    # composite decking high estimate ($/sqft)
DRIVEWAY_ESTIMATE_SQFT  = 400   # typical driveway/garage pad area
DECK_RATIO_LOW          = 0.15  # min % of available outdoor used for deck
DECK_RATIO_HIGH         = 0.30  # max % of available outdoor used for deck

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

# ─── SanGIS / SANDAG — Primary parcel data (FREE, no key) ───────────────────
SANDAG_PARCELS_URL = "https://geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0/query"
SANGIS_MAX_RECORDS  = 2000   # ArcGIS REST limit per query (paginate if needed)
SANGIS_TIMEOUT      = 30     # seconds per request

# ─── Overpass API (OSM) — used for commercial/restaurant data only ──────────
OVERPASS_FALLBACK_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
OVERPASS_TIMEOUT = 60
