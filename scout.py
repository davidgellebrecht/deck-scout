#!/usr/bin/env python3
"""
scout.py — Property data fetching and filtering for Deck Scout.

Primary data source: SanGIS/SANDAG ArcGIS REST API (free, no key needed).
Provides real San Diego County parcel data: APN, address, year built,
assessed value, lot size, land use, bedrooms, baths, pool status.

Commercial data (restaurants): OpenStreetMap Overpass API.
"""

import math
import time
from datetime import date, timedelta

import requests

import config


# ─── Geometry ─────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    R = 6_371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ─── SanGIS / SANDAG API ─────────────────────────────────────────────────────

# Land use codes: 100-199 = residential
# 100 = vacant residential, 110 = single family, 111 = SFR with granny flat,
# 120 = condo, 130 = cooperative, 140 = duplex-4plex, 150 = 5+ units,
# 160 = mobile home, 170 = misc residential
RESIDENTIAL_USE_CODES = set(range(100, 200))
COMMERCIAL_USE_CODES  = set(range(200, 300))  # 200-299 = commercial


def _parse_year(year_eff: str) :
    """Parse the 2-digit year_effective field into a 4-digit year."""
    if not year_eff or year_eff == "00":
        return None
    try:
        yy = int(str(year_eff).strip())
        if yy == 0:
            return None
        # 2-digit: 26+ → 1926+, 00-25 → 2000-2025
        if yy >= 26:
            return 1900 + yy
        else:
            return 2000 + yy
    except (ValueError, TypeError):
        return None


def _parse_docdate(docdate: str) :
    """Parse MMDDYY docdate (last transfer date) into a date object."""
    if not docdate or len(str(docdate).strip()) < 6:
        return None
    try:
        s = str(docdate).strip()
        mm = int(s[:2])
        dd = int(s[2:4])
        yy = int(s[4:6])
        year = 2000 + yy if yy < 50 else 1900 + yy
        if mm < 1 or mm > 12 or dd < 1 or dd > 31:
            return None
        return date(year, mm, dd)
    except (ValueError, TypeError, IndexError):
        return None


def _parse_lot_sqft(attrs: dict) :
    """Extract lot size in sqft from SANDAG data."""
    # Try usable_sq_feet first (more accurate)
    usable = attrs.get("usable_sq_feet", "")
    if usable and str(usable).strip():
        try:
            val = int(str(usable).strip())
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass
    # Fall back to SHAPE__Area (polygon area in sq feet)
    shape_area = attrs.get("SHAPE__Area")
    if shape_area:
        try:
            return int(float(shape_area))
        except (ValueError, TypeError):
            pass
    return None


def _polygon_centroid(rings: list) -> tuple:
    """Compute centroid from ArcGIS polygon rings."""
    if not rings or not rings[0]:
        return None, None
    pts = rings[0]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _build_address(attrs: dict) -> str:
    """Build a readable address from SANDAG fields."""
    parts = []
    addr = str(attrs.get("situs_address", "") or "").strip()
    pre_dir = str(attrs.get("situs_pre_dir", "") or "").strip()
    street = str(attrs.get("situs_street", "") or "").strip()
    suffix = str(attrs.get("situs_suffix", "") or "").strip()
    post_dir = str(attrs.get("situs_post_dir", "") or "").strip()
    suite = str(attrs.get("situs_suite", "") or "").strip()

    if addr and addr != "0":
        parts.append(addr)
    if pre_dir:
        parts.append(pre_dir)
    if street:
        parts.append(street)
    if suffix:
        parts.append(suffix)
    if post_dir:
        parts.append(post_dir)

    address = " ".join(parts)
    if suite:
        address += f" #{suite}"

    community = str(attrs.get("situs_community", "") or "").strip()
    if community:
        address += f", {community}"

    zipcode = str(attrs.get("situs_zip", "") or "").strip()
    if zipcode:
        address += f" {zipcode}"

    return address or "Unknown Address"


def fetch_residential_properties() -> list:
    """
    Fetch residential parcels from SANDAG ArcGIS REST API.
    Returns real San Diego County property data with assessed values,
    year built, lot sizes, and addresses.
    """
    s, w, n, e = config.CITY_BBOX

    # Query fields
    out_fields = (
        "apn,situs_address,situs_pre_dir,situs_street,situs_suffix,"
        "situs_post_dir,situs_suite,situs_community,situs_zip,"
        "year_effective,acreage,asr_total,asr_land,asr_impr,"
        "nucleus_use_cd,bedrooms,baths,total_lvg_area,pool,"
        "docdate,SHAPE__Area,usable_sq_feet"
    )

    all_features = []
    offset = 0
    max_records = config.SANGIS_MAX_RECORDS

    while True:
        params = {
            "where": "nucleus_use_cd >= '100' AND nucleus_use_cd < '200'",
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": out_fields,
            "returnGeometry": "true",
            "f": "json",
            "resultRecordCount": max_records,
            "resultOffset": offset,
        }

        try:
            resp = requests.get(
                config.SANDAG_PARCELS_URL,
                params=params,
                timeout=config.SANGIS_TIMEOUT,
                headers={"User-Agent": "DeckScout/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  WARNING: SANDAG query failed (offset {offset}): {e}")
            break

        if "error" in data:
            print(f"  WARNING: SANDAG API error: {data['error'].get('message', '')}")
            break

        features = data.get("features", [])
        all_features.extend(features)
        print(f"  SANDAG: fetched {len(features)} parcels (total: {len(all_features)})")

        # Check if there are more pages
        if len(features) < max_records:
            break
        offset += max_records

        # Safety limit
        if len(all_features) >= 10_000:
            print(f"  WARNING: Hit 10,000 parcel limit — stopping pagination")
            break

    # Parse features into property dicts
    properties = []
    for feat in all_features:
        attrs = feat.get("attributes", {})
        geom = feat.get("geometry", {})

        # Get centroid from polygon
        rings = geom.get("rings", [])
        lon, lat = _polygon_centroid(rings)
        if not lat or not lon:
            continue

        # Parse fields
        year_built = _parse_year(attrs.get("year_effective"))
        lot_sqft = _parse_lot_sqft(attrs)
        assessed_value = attrs.get("asr_total")
        if assessed_value and isinstance(assessed_value, (int, float)) and assessed_value > 0:
            assessed_value = int(assessed_value)
        else:
            assessed_value = None

        sale_date = _parse_docdate(attrs.get("docdate"))
        address = _build_address(attrs)
        apn = str(attrs.get("apn", "")).strip()

        # Land use code → property type
        use_code = 0
        try:
            use_code = int(str(attrs.get("nucleus_use_cd", "0")).strip())
        except (ValueError, TypeError):
            pass

        if use_code in RESIDENTIAL_USE_CODES:
            property_type = "residential"
        elif use_code in COMMERCIAL_USE_CODES:
            property_type = "commercial"
        else:
            property_type = "residential"

        # Building type from use code
        if use_code == 110 or use_code == 111:
            building_type = "house"
        elif use_code == 120:
            building_type = "condo"
        elif use_code in (140, 141):
            building_type = "duplex"
        elif use_code >= 150 and use_code < 160:
            building_type = "apartments"
        elif use_code == 160:
            building_type = "mobile_home"
        elif use_code == 100:
            building_type = "vacant_residential"
        else:
            building_type = "residential"

        bedrooms = str(attrs.get("bedrooms", "")).strip()
        baths = str(attrs.get("baths", "")).strip()
        has_pool = str(attrs.get("pool", "")).strip().upper() == "Y"
        living_area = attrs.get("total_lvg_area", 0) or 0

        prop = {
            "lat":              float(lat),
            "lon":              float(lon),
            "apn":              apn,
            "address":          address,
            "year_built":       year_built,
            "building_type":    building_type,
            "material":         "",  # Not in SANDAG data
            "lot_sqft":         lot_sqft,
            "assessed_value":   assessed_value,
            "sale_date":        sale_date,
            "property_type":    property_type,
            "land_use_code":    use_code,
            "bedrooms":         bedrooms,
            "baths":            baths,
            "living_area_sqft": int(living_area) if living_area else 0,
            "has_pool":         has_pool,
            "gps_coordinates":  f"{float(lat):.5f}, {float(lon):.5f}",
            "parcel_rings":     rings,  # polygon boundary for map display
        }
        properties.append(prop)

    return properties


# ─── Overpass API (for commercial/restaurant data) ───────────────────────────

def _overpass(query: str, retries: int = 3, backoff: int = 15) -> dict:
    """POST an Overpass QL query with retry and fallback mirrors."""
    http_timeout = config.OVERPASS_TIMEOUT + 10

    for url in config.OVERPASS_FALLBACK_URLS:
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, data={"data": query}, timeout=http_timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                print(f"  WARNING: Overpass timed out at {url} (attempt {attempt}/{retries}).")
                if attempt < retries:
                    time.sleep(backoff)
            except requests.exceptions.HTTPError:
                code = resp.status_code
                if code == 429:
                    wait = backoff * 2
                    print(f"  WARNING: Overpass rate-limited — waiting {wait}s...")
                    if attempt < retries:
                        time.sleep(wait)
                elif code >= 500:
                    if attempt < retries:
                        time.sleep(backoff)
                else:
                    break
            except requests.exceptions.RequestException as exc:
                print(f"  WARNING: Overpass request failed — {exc}")
                if attempt < retries:
                    time.sleep(backoff)

    print("  ERROR: All Overpass mirrors failed.")
    return {"elements": []}


def fetch_commercial_properties() -> list:
    """
    Fetch restaurants/cafes with outdoor seating from OSM.
    Used for the commercial signal layers.
    """
    s, w, n, e = config.CITY_BBOX
    query = f"""
    [out:json][timeout:{config.OVERPASS_TIMEOUT}];
    (
      node["amenity"~"restaurant|cafe|bar"]["outdoor_seating"="yes"]({s},{w},{n},{e});
      way["amenity"~"restaurant|cafe|bar"]["outdoor_seating"="yes"]({s},{w},{n},{e});
      node["amenity"~"restaurant|cafe|bar"]({s},{w},{n},{e});
      way["amenity"~"restaurant|cafe|bar"]({s},{w},{n},{e});
    );
    out center tags;
    """
    data = _overpass(query)
    elements = data.get("elements", [])

    properties = []
    for el in elements:
        center = el.get("center", {})
        lat = el.get("lat") or center.get("lat")
        lon = el.get("lon") or center.get("lon")
        if not lat or not lon:
            continue

        tags = el.get("tags", {})
        name = tags.get("name", "Unnamed Restaurant")
        has_outdoor = tags.get("outdoor_seating", "") == "yes"

        prop = {
            "lat":              float(lat),
            "lon":              float(lon),
            "osm_id":           el.get("id"),
            "osm_type":         el.get("type"),
            "address":          name,
            "name":             name,
            "property_type":    "commercial",
            "amenity":          tags.get("amenity", ""),
            "has_outdoor_seating": has_outdoor,
            "cuisine":          tags.get("cuisine", ""),
            "gps_coordinates":  f"{float(lat):.5f}, {float(lon):.5f}",
        }
        properties.append(prop)

    return properties


# ─── Filtering ───────────────────────────────────────────────────────────────

def filter_properties(properties: list) -> tuple:
    """
    Apply hard filters from config.FILTERS.
    Returns (passed, skipped_counts).
    """
    passed = []
    skipped = {"property_value": 0, "lot_size": 0, "property_type": 0, "new_construction": 0}

    current_year = date.today().year
    prop_type_filter = config.FILTERS.get("property_type", "All")

    for prop in properties:
        # Filter: minimum property value
        if config.FILTERS["min_property_value"]:
            val = prop.get("assessed_value")
            if val is not None and val < config.MIN_PROPERTY_VALUE:
                skipped["property_value"] += 1
                continue

        # Filter: minimum lot size
        if config.FILTERS["min_lot_size"]:
            lot = prop.get("lot_sqft")
            if lot is not None and lot < config.MIN_LOT_SQFT:
                skipped["lot_size"] += 1
                continue

        # Filter: property type
        if prop_type_filter != "All":
            ptype = (prop.get("property_type") or "residential").lower()
            if prop_type_filter == "Residential" and ptype == "commercial":
                skipped["property_type"] += 1
                continue
            if prop_type_filter == "Commercial" and ptype != "commercial":
                skipped["property_type"] += 1
                continue

        # Filter: exclude new construction
        if config.FILTERS["exclude_new_construction"]:
            yb = prop.get("year_built")
            if yb and (current_year - yb) < config.NEW_CONSTRUCTION_YEARS:
                skipped["new_construction"] += 1
                continue

        passed.append(prop)

    return passed, skipped


# ─── Banner ──────────────────────────────────────────────────────────────────

def print_banner(filters: dict):
    print(f"\n{'═' * 60}")
    print(f"  Deck Scout — {config.CITY}")
    print(f"  Bbox: {config.CITY_BBOX}")
    active = [k for k, v in filters.items() if v]
    print(f"  Active filters: {', '.join(active) or 'None'}")
    print(f"  Data source: SanGIS/SANDAG + OSM")
    print(f"{'═' * 60}\n")
