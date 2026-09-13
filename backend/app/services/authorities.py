"""Civic authority resolution and municipal boundary registry with Reverse Geocoding support."""

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

logger = logging.getLogger("okdriver.authorities")


@dataclass
class CivicAuthority:
    """Represents a municipal or regional road maintenance authority."""
    code: str
    name: str
    region: str
    contact_email: str
    api_endpoint: str
    description: str
    # Bounding box coordinates: (min_lat, max_lat, min_lon, max_lon)
    bounds: Optional[Tuple[float, float, float, float]] = None
    # Reverse geocoded granular address fields
    location_name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


# Municipal Authorities Registry for Major Metros (Fast-Path)
AUTHORITIES: List[CivicAuthority] = [
    CivicAuthority(
        code="BMC",
        name="Brihanmumbai Municipal Corporation (BMC)",
        region="Mumbai Metropolitan Region",
        contact_email="roads.maintenance@mcgm.gov.in",
        api_endpoint="https://api.mcgm.gov.in/v1/pothole-grievance",
        description="Responsible for maintenance and asphalt resurfacing of Mumbai city and suburban roads.",
        bounds=(18.89, 19.30, 72.75, 73.05),
        city="Mumbai",
        state="Maharashtra",
    ),
    CivicAuthority(
        code="MCD",
        name="Municipal Corporation of Delhi (MCD)",
        region="National Capital Territory of Delhi",
        contact_email="roadworks@mcd.nic.in",
        api_endpoint="https://mcdonline.nic.in/api/v2/road-incidents",
        description="Oversees arterial road repair and municipal infrastructure in Delhi NCR.",
        bounds=(28.40, 28.88, 76.84, 77.40),
        city="Delhi",
        state="Delhi",
    ),
    CivicAuthority(
        code="BBMP",
        name="Bruhat Bengaluru Mahanagara Palike (BBMP)",
        region="Bengaluru Urban",
        contact_email="fixpotholes@bbmp.gov.in",
        api_endpoint="https://bbmp.gov.in/api/v1/grievance/potholes",
        description="Manages urban road maintenance, stormwater drain integrity, and asphalt filling in Bengaluru.",
        bounds=(12.80, 13.15, 77.45, 77.78),
        city="Bengaluru",
        state="Karnataka",
    ),
    CivicAuthority(
        code="SFDPW",
        name="San Francisco Public Works (SFDPW)",
        region="San Francisco Bay Area",
        contact_email="potholes@sfdpw.org",
        api_endpoint="https://sf311.org/api/v2/requests/pothole",
        description="Maintains street infrastructure, asphalt repair, and pothole patching across San Francisco.",
        bounds=(37.70, 37.85, -122.53, -122.35),
        city="San Francisco",
        state="California",
    ),
]

# Fallback Authority for offline or undefined coordinates
FALLBACK_AUTHORITY = CivicAuthority(
    code="PWD_CENTRAL",
    name="Public Works Department (PWD / NHAI)",
    region="National / State Highways & Regional Roads",
    contact_email="highway.maintenance@nhai.org",
    api_endpoint="https://nhai.org/api/v1/incident-reports",
    description="Jurisdiction for state highways, national expressways, and regional roads outside specific municipal corporations.",
    bounds=None,
    city="National Highways",
    state="India",
)


# ============================================================================
# Reverse Geocoding Engine (OpenStreetMap / Nominatim with LRU Cache)
# ============================================================================

@lru_cache(maxsize=1024)
def _reverse_geocode_cached(lat_rounded: float, lon_rounded: float) -> Optional[str]:
    """Query OpenStreetMap Nominatim reverse geocode API with caching."""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat_rounded}&lon={lon_rounded}&format=json"
    headers = {
        "User-Agent": "okDRIVER-CivicAudit-System/1.0 (https://okdriver.ai; civic-audit@okdriver.ai)",
        "Accept-Language": "en",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3.5) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
    except Exception as exc:
        logger.warning(f"Reverse geocoding lookup failed for ({lat_rounded}, {lon_rounded}): {exc}")
    return None


def reverse_geocode(latitude: float, longitude: float) -> dict:
    """Reverse geocode GPS coordinates with 4-decimal precision caching (~11 meters)."""
    lat_r = round(latitude, 4)
    lon_r = round(longitude, 4)
    raw = _reverse_geocode_cached(lat_r, lon_r)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def resolve_small_city_authority(addr: dict, lat: float, lon: float) -> CivicAuthority:
    """Dynamically determine civic authority (Nagar Nigam, Nagar Palika, State PWD, NHAI) from reverse-geocoded address."""
    road = addr.get("road") or addr.get("highway") or ""
    suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("residential") or ""
    city = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or addr.get("hamlet") or ""
    district = addr.get("county") or addr.get("state_district") or addr.get("district") or ""
    state = addr.get("state") or "India"
    pincode = addr.get("postcode") or ""

    # Human-readable street / locality name
    loc_parts = [p for p in [road, suburb, city] if p]
    location_name = ", ".join(loc_parts) if loc_parts else f"GPS ({lat:.4f}, {lon:.4f})"

    # 1. National Highway check (e.g. NH-48, NH-19, National Highway 2)
    is_national_highway = bool(re.search(r"\bNH\b|\bNational Highway\b", road, re.IGNORECASE))
    if is_national_highway:
        st_abbr = re.sub(r'[^A-Z]', '', state.upper())[:2] or "IN"
        return CivicAuthority(
            code=f"NHAI_{st_abbr}",
            name=f"National Highways Authority of India (NHAI - {district or state} Division)",
            region=f"{road}, {district or state}",
            contact_email=f"nhai.{district.lower().replace(' ', '') if district else 'roads'}@nhai.org",
            api_endpoint="https://nhai.org/api/v1/incident-reports",
            description=f"Jurisdiction for National Highway corridor ({road}) in {district or state}.",
            location_name=location_name,
            city=city or district,
            district=district,
            state=state,
            pincode=pincode,
        )

    # 2. State Highway check (e.g. SH-13, SH-1, State Highway)
    is_state_highway = bool(re.search(r"\bSH\b|\bState Highway\b", road, re.IGNORECASE))
    if is_state_highway:
        st_abbr = re.sub(r'[^A-Z]', '', state.upper())[:2] or "ST"
        return CivicAuthority(
            code=f"PWD_{st_abbr}_SH",
            name=f"{state} Public Works Department (State Highway Division)",
            region=f"{road}, {district or state}",
            contact_email=f"pwd.highways@{state.lower().replace(' ', '')}.gov.in",
            api_endpoint=f"https://pwd.{state.lower().replace(' ', '')}.gov.in/api/v1/defects",
            description=f"Responsible for state highway maintenance ({road}) in {district or state}.",
            location_name=location_name,
            city=city or district,
            district=district,
            state=state,
            pincode=pincode,
        )

    # 3. Urban Local Body in Small City or Town (Nagar Nigam / Nagar Palika / Nagar Parishad)
    if city:
        city_clean = city.strip()
        city_code = re.sub(r'[^A-Z]', '', city_clean.upper())[:4] or "CITY"

        # Tier-2 Municipal Corporations
        tier2_cities = ["meerut", "agra", "varanasi", "indore", "bhopal", "patna", "nagpur", "surat", "vadodara", "kanpur", "lucknow", "ghaziabad", "prayagraj"]
        if any(c in city_clean.lower() for c in tier2_cities):
            ulb_label = "Nagar Nigam (Municipal Corporation)"
            code = f"{city_code}_NN"
        else:
            ulb_label = "Nagar Palika Parishad (Municipal Council)"
            code = f"{city_code}_NP"

        return CivicAuthority(
            code=code,
            name=f"{city_clean} {ulb_label}",
            region=f"{city_clean}, {district or state}",
            contact_email=f"commissioner.{city_clean.lower().replace(' ', '')}@{state.lower().replace(' ', '')}.gov.in",
            api_endpoint=f"https://{city_clean.lower().replace(' ', '')}.ulb.gov.in/api/v1/grievance",
            description=f"Local municipal body responsible for arterial streets, stormwater paving, and asphalt restoration in {city_clean}.",
            location_name=location_name,
            city=city_clean,
            district=district,
            state=state,
            pincode=pincode,
        )

    # 4. District / Rural Road -> District PWD
    st_abbr = re.sub(r'[^A-Z]', '', state.upper())[:2] or "PWD"
    dist_code = re.sub(r'[^A-Z]', '', (district or "DIST").upper())[:4]
    return CivicAuthority(
        code=f"PWD_{st_abbr}_{dist_code}",
        name=f"{state} Public Works Department ({district or 'District'} Division)",
        region=f"{district or 'District Road'}, {state}",
        contact_email=f"pwd.{district.lower().replace(' ', '') if district else 'roads'}@{state.lower().replace(' ', '')}.gov.in",
        api_endpoint=f"https://pwd.{state.lower().replace(' ', '')}.gov.in/api/v1/tickets",
        description=f"District road maintenance division in charge of regional links in {district or state}.",
        location_name=location_name,
        city=district or "District Road",
        district=district,
        state=state,
        pincode=pincode,
    )


def resolve_authority(latitude: float, longitude: float) -> CivicAuthority:
    """Resolve the responsible civic authority for any GPS coordinate in India."""
    # 1. Fast path: check known major metros
    for auth in AUTHORITIES:
        if auth.bounds:
            min_lat, max_lat, min_lon, max_lon = auth.bounds
            if min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon:
                return auth

    # 2. Dynamic Reverse Geocoding for Small Cities, Towns, Highways, and Districts
    geo_data = reverse_geocode(latitude, longitude)
    if geo_data and "address" in geo_data:
        return resolve_small_city_authority(geo_data["address"], latitude, longitude)

    # 3. Safe fallback if network / geocoder unavailable
    return FALLBACK_AUTHORITY


def get_authority_by_code(code: str) -> Optional[CivicAuthority]:
    """Look up an authority by its short code."""
    code_upper = code.upper().strip()
    if code_upper == FALLBACK_AUTHORITY.code:
        return FALLBACK_AUTHORITY
    for auth in AUTHORITIES:
        if auth.code == code_upper:
            return auth
    return None


def list_authorities() -> List[CivicAuthority]:
    """List all registered civic authorities including fallback."""
    return list(AUTHORITIES) + [FALLBACK_AUTHORITY]
