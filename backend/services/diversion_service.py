"""
CrowdFlow — Diversion Service
================================
Rule-based response plan generation combining ML predictions with
operational logic for barricade counts, diversions, and deployment.
"""

import math
from typing import List, Dict, Optional

# ---------------------------------------------------------------------------
# Police station coordinates (approximate centroids from data)
# ---------------------------------------------------------------------------
POLICE_STATIONS = {
    "Yelahanka": {"lat": 13.1005, "lon": 77.5960},
    "HAL Old Airport": {"lat": 12.9500, "lon": 77.6680},
    "Sadashivanagar": {"lat": 13.0070, "lon": 77.5790},
    "Byatarayanapura": {"lat": 13.0670, "lon": 77.5950},
    "Halasuru Gate": {"lat": 12.9780, "lon": 77.6080},
    "Yeshwanthpura": {"lat": 13.0280, "lon": 77.5450},
    "Hennuru": {"lat": 13.0340, "lon": 77.6430},
    "Kodigehalli": {"lat": 13.0640, "lon": 77.5730},
    "Banaswadi": {"lat": 13.0110, "lon": 77.6510},
    "K.R. Pura": {"lat": 13.0020, "lon": 77.7020},
    "Kamakshipalya": {"lat": 12.9900, "lon": 77.5280},
    "Cubbon Park": {"lat": 12.9763, "lon": 77.5929},
    "Jalahalli": {"lat": 13.0440, "lon": 77.5440},
    "Chamarajpet": {"lat": 12.9570, "lon": 77.5680},
    "Peenya": {"lat": 13.0310, "lon": 77.5180},
    "HSR Layout": {"lat": 12.9116, "lon": 77.6389},
    "Wilson Garden": {"lat": 12.9468, "lon": 77.5974},
    "Shivajinagar": {"lat": 12.9857, "lon": 77.6057},
    "Whitefield": {"lat": 12.9698, "lon": 77.7500},
    "Electronic City": {"lat": 12.8440, "lon": 77.6720},
    "Madiwala": {"lat": 12.9226, "lon": 77.6170},
    "Mahadevapura": {"lat": 12.9965, "lon": 77.6950},
    "Jayanagara": {"lat": 12.9308, "lon": 77.5838},
    "Malleshwaram": {"lat": 13.0035, "lon": 77.5703},
    "Rajajinagar": {"lat": 12.9940, "lon": 77.5520},
    "Basavanagudi": {"lat": 12.9430, "lon": 77.5730},
    "Halasur": {"lat": 12.9800, "lon": 77.6160},
    "J.P. Nagar": {"lat": 12.9063, "lon": 77.5857},
    "Magadi Road": {"lat": 12.9630, "lon": 77.5230},
    "R.T. Nagar": {"lat": 13.0220, "lon": 77.5970},
    "Ashok Nagar": {"lat": 12.9595, "lon": 77.5820},
    "Kengeri": {"lat": 12.9060, "lon": 77.4830},
    "Bellandur": {"lat": 12.9260, "lon": 77.6760},
    "Vijayanagara": {"lat": 12.9710, "lon": 77.5330},
    "Banashankari": {"lat": 12.9250, "lon": 77.5460},
}

# Major corridors with suggested alternate routes
DIVERSION_ROUTES = {
    "Bellary Road 1": [
        "Sankey Road → Palace Road → Cunningham Road",
        "Sadashivanagar Main Road → Armane Nagar",
    ],
    "Bellary Road 2": [
        "Hebbal Flyover → Outer Ring Road → Yelahanka",
        "NH44 via Jakkur Main Road",
    ],
    "Mysore Road": [
        "Chord Road → Vijayanagar → Kengeri",
        "NICE Road (toll) → Rajarajeshwari Nagar",
    ],
    "Tumkur Road": [
        "Peenya Industrial Area Internal Roads",
        "Outer Ring Road → Yeshwanthpura",
    ],
    "Hosur Road": [
        "BTM Layout → Bannerghatta Road → Electronic City",
        "Silk Board → ORR East → Marathahalli",
    ],
    "Old Madras Road": [
        "Indiranagar → HAL Airport Road → KR Pura",
        "ORR East via Marathahalli",
    ],
    "Bannerghata Road": [
        "JP Nagar → BTM Layout → Hosur Road",
        "Jayanagar → Kanakapura Road",
    ],
    "Magadi Road": [
        "Chord Road → Rajajinagar",
        "Mysore Road via Nayandahalli",
    ],
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_nearest_police_stations(lat: float, lon: float, top_n: int = 3) -> List[Dict]:
    """Find the N nearest police stations to a given location."""
    distances = []
    for name, coords in POLICE_STATIONS.items():
        dist = haversine_distance(lat, lon, coords["lat"], coords["lon"])
        distances.append({
            "name": name,
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "distance_km": round(dist, 2),
        })
    distances.sort(key=lambda x: x["distance_km"])
    return distances[:top_n]


def generate_diversion_plan(
    severity: str,
    latitude: float,
    longitude: float,
    requires_road_closure: bool,
    event_cause: str,
    corridor: str = "Non-corridor",
    zone: str = "Unknown",
    manpower_needed: str = "1-2",
    police_station: str = None,
) -> Dict:
    """
    Generate a rule-based response plan combining severity predictions
    with operational logic.

    This is NOT an ML model — it's a deterministic business logic layer
    that combines the ML predictions with domain rules.
    """

    # --- Barricade count based on severity + road closure ---
    barricade_map = {
        ("Critical", True): 8,
        ("Critical", False): 5,
        ("High", True): 5,
        ("High", False): 3,
        ("Medium", True): 3,
        ("Medium", False): 1,
        ("Low", True): 2,
        ("Low", False): 0,
    }
    barricades = barricade_map.get((severity, requires_road_closure), 2)

    # Extra barricades for high-impact event causes
    if event_cause in ["accident", "protest", "vip_movement", "public_event"]:
        barricades += 2

    # --- Officer count recommendation ---
    officer_map = {
        "10+": "12-15 officers",
        "6-10": "6-10 officers",
        "3-5": "3-5 officers",
        "1-2": "1-2 officers",
    }
    officers = officer_map.get(manpower_needed, "3-5 officers")

    # --- Diversion routes ---
    diversions = []
    if requires_road_closure or severity in ["High", "Critical"]:
        # Check if corridor has predefined diversions
        for corr_name, routes in DIVERSION_ROUTES.items():
            if corr_name.lower() in corridor.lower():
                diversions = routes
                break

        if not diversions:
            # Generic diversions
            diversions = [
                "Use parallel internal roads",
                "Reroute via nearest Outer Ring Road segment",
            ]

    # --- Nearest police stations for deployment ---
    nearest_stations = get_nearest_police_stations(latitude, longitude, top_n=3)

    # --- Alert level ---
    alert_levels = {
        "Critical": "🔴 RED ALERT — Immediate deployment required",
        "High": "🟠 ORANGE ALERT — Priority deployment",
        "Medium": "🟡 YELLOW ALERT — Standard response",
        "Low": "🟢 GREEN — Monitor situation",
    }
    alert = alert_levels.get(severity, "🟡 YELLOW ALERT")

    # --- Action summary ---
    actions = []
    if severity == "Critical":
        actions.append("Activate emergency traffic management protocol")
        actions.append(f"Deploy {officers} immediately from nearest stations")
        if requires_road_closure:
            actions.append(f"Set up {barricades} barricades for full road closure")
            actions.append("Activate electronic diversion signage")
        actions.append("Alert traffic control room for real-time coordination")
    elif severity == "High":
        actions.append(f"Deploy {officers} for traffic management")
        if requires_road_closure:
            actions.append(f"Set up {barricades} barricades for partial/full closure")
        actions.append("Monitor situation and prepare escalation plan")
    elif severity == "Medium":
        actions.append(f"Assign {officers} for on-site management")
        if barricades > 0:
            actions.append(f"Place {barricades} warning barricades")
        actions.append("Coordinate with nearest police station")
    else:
        actions.append(f"Assign {officers} for monitoring")
        actions.append("Standard traffic advisory if needed")

    if event_cause in ["accident", "tree_fall"]:
        actions.append("Dispatch clearing/towing crew")
    if event_cause == "water_logging":
        actions.append("Alert BBMP storm water drain team")
    if event_cause == "vip_movement":
        actions.append("Coordinate with SPG/security detail")

    summary = " → ".join(actions)

    return {
        "severity": severity,
        "recommended_barricades": barricades,
        "recommended_officers": officers,
        "road_closure_needed": requires_road_closure,
        "diversion_routes": diversions,
        "nearest_police_stations": nearest_stations,
        "action_summary": summary,
        "alert_level": alert,
    }
