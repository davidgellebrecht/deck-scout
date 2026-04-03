#!/usr/bin/env python3
"""
scout.py — Property data fetching and filtering for Deck Scout.

Fetches residential property data from public sources and applies
hard filters defined in config.py. Unlike Parcel Scout (which queries
OSM for agricultural parcels), Deck Scout focuses on residential
properties with deck/maintenance potential.
"""

import math
import time
from datetime import date

import requests

import config


# ─── Overpass API ─────────────────────────────────────────────────────────────

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
                    print(f"  WARNING: Overpass rate-limited at {url} — waiting {wait}s...")
                    if attempt < retries:
                        time.sleep(wait)
                elif code >= 500:
                    print(f"  WARNING: Overpass {code} at {url} — retrying...")
                    if attempt < retries:
                        time.sleep(backoff)
                else:
                    break
            except requests.exceptions.RequestException as exc:
                print(f"  WARNING: Overpass request failed — {exc}")
                if attempt < retries:
                    time.sleep(backoff)

    print("  ERROR: All Overpass mirrors failed. Returning empty result set.")
    return {"elements": []}


def _bbox() -> str:
    s, w, n, e = config.CITY_BBOX
    return f"{s},{w},{n},{e}"


# ─── Geometry ─────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    R = 6_371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ─── Property fetching ───────────────────────────────────────────────────────

def fetch_residential_properties() -> list:
    """
    Fetch residential buildings from OpenStreetMap within the city bbox.
    Returns a list of property dicts with lat, lon, and available tags.
    """
    bbox = _bbox()
    query = f"""
    [out:json][timeout:{config.OVERPASS_TIMEOUT}];
    (
      way["building"~"house|residential|detached|semidetached_house|apartments|terrace"]({bbox});
      way["building"="yes"]["addr:housenumber"]({bbox});
      relation["building"~"house|residential|detached"]({bbox});
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

        # Build address from OSM tags
        street = tags.get("addr:street", "")
        number = tags.get("addr:housenumber", "")
        city = tags.get("addr:city", "")
        postcode = tags.get("addr:postcode", "")
        address = f"{number} {street}".strip()
        if city:
            address += f", {city}"
        if postcode:
            address += f" {postcode}"

        # Extract year built if available
        year_built = None
        start_date = tags.get("start_date", "")
        if start_date:
            try:
                year_built = int(start_date[:4])
            except (ValueError, IndexError):
                pass

        # Extract building material
        material = tags.get("building:material", "")

        prop = {
            "lat":            float(lat),
            "lon":            float(lon),
            "osm_id":         el.get("id"),
            "osm_type":       el.get("type"),
            "address":        address or f"{float(lat):.5f}, {float(lon):.5f}",
            "year_built":     year_built,
            "building_type":  tags.get("building", "residential"),
            "building_levels": tags.get("building:levels"),
            "material":       material,
            "lot_sqft":       None,  # OSM doesn't reliably have lot size
            "assessed_value": None,  # Not in OSM
            "sale_date":      None,  # Not in OSM
            "property_type":  "residential",
            "gps_coordinates": f"{float(lat):.5f}, {float(lon):.5f}",
        }
        properties.append(prop)

    return properties


def fetch_commercial_properties() -> list:
    """
    Fetch restaurants/cafes with outdoor seating from OSM.
    Used for the commercial signal layers.
    """
    bbox = _bbox()
    query = f"""
    [out:json][timeout:{config.OVERPASS_TIMEOUT}];
    (
      node["amenity"~"restaurant|cafe|bar"]["outdoor_seating"="yes"]({bbox});
      way["amenity"~"restaurant|cafe|bar"]["outdoor_seating"="yes"]({bbox});
      node["amenity"~"restaurant|cafe|bar"]({bbox});
      way["amenity"~"restaurant|cafe|bar"]({bbox});
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
    print(f"{'═' * 60}\n")
