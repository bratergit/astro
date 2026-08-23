"""
Astrocartography engine.

Calculates, for a given birth date/time (defaulting to 12:00 UTC when no
time is supplied — matches the disclaimer text in the UI), where each
classical planet is "angular" (on the Ascendant, Descendant, Midheaven or
Imum Coeli) around the globe, then ranks a built-in list of world cities by
proximity to the "favorable" planetary lines (Sun, Moon, Venus, Jupiter).

Uses a pure-Python low-precision ephemeris (simple_ephemeris.py) — no
compiled/binary dependency, so it can't break due to Python-version wheel
mismatches on any hosting platform (this replaces an earlier pyswisseph
version that broke on Python 3.14 for exactly that reason).

This is astrology, presented here in the same spirit as the rest of the app
(numerology, ley lines, biorhythms): a structured, deterministic calculation
with no established scientific predictive validity. It is entertainment.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import simple_ephemeris as ephem

# --- PLANETS ---
PLANETS = {
    "Sol": "sun",
    "Lua": "moon",
    "Mercúrio": "mercury",
    "Vênus": "venus",
    "Marte": "mars",
    "Júpiter": "jupiter",
    "Saturno": "saturn",
}

FAVORABLE_PLANETS = {"Sol", "Lua", "Vênus", "Júpiter"}

PLANET_MEANINGS = {
    "Sol": "vitalidade, sucesso, brilho pessoal e reconhecimento",
    "Lua": "lar, família, acolhimento emocional e intuição",
    "Vênus": "amor, beleza, harmonia, arte e prazer",
    "Júpiter": "sorte, expansão, prosperidade e oportunidades",
    "Mercúrio": "comunicação, aprendizado, comércio e agilidade mental",
    "Marte": "energia, coragem, ação e iniciativa (pode trazer conflitos)",
    "Saturno": "disciplina, responsabilidade, estrutura e maturidade (pode trazer desafios)",
}

ANGLE_NAMES = {
    "AC": "Ascendente",
    "DC": "Descendente",
    "MC": "Meio-Céu",
    "IC": "Fundo do Céu",
}

# --- BUILT-IN CITY DATABASE (lat, lon, país) ---
WORLD_CITIES: List[Tuple[str, str, float, float]] = [
    ("Dublin", "Irlanda", 53.3498, -6.2603),
    ("Londres", "Reino Unido", 51.5074, -0.1278),
    ("Paris", "França", 48.8566, 2.3522),
    ("Lisboa", "Portugal", 38.7223, -9.1393),
    ("Madri", "Espanha", 40.4168, -3.7038),
    ("Roma", "Itália", 41.9028, 12.4964),
    ("Amsterdã", "Holanda", 52.3676, 4.9041),
    ("Berlim", "Alemanha", 52.5200, 13.4050),
    ("Viena", "Áustria", 48.2082, 16.3738),
    ("Zurique", "Suíça", 47.3769, 8.5417),
    ("Estocolmo", "Suécia", 59.3293, 18.0686),
    ("Copenhague", "Dinamarca", 55.6761, 12.5683),
    ("Nova York", "EUA", 40.7128, -74.0060),
    ("Los Angeles", "EUA", 34.0522, -118.2437),
    ("São Francisco", "EUA", 37.7749, -122.4194),
    ("Miami", "EUA", 25.7617, -80.1918),
    ("Chicago", "EUA", 41.8781, -87.6298),
    ("Toronto", "Canadá", 43.6532, -79.3832),
    ("Vancouver", "Canadá", 49.2827, -123.1207),
    ("Cidade do México", "México", 19.4326, -99.1332),
    ("São Paulo", "Brasil", -23.5505, -46.6333),
    ("Rio de Janeiro", "Brasil", -22.9068, -43.1729),
    ("Brasília", "Brasil", -15.7939, -47.8828),
    ("Buenos Aires", "Argentina", -34.6037, -58.3816),
    ("Santiago", "Chile", -33.4489, -70.6693),
    ("Bogotá", "Colômbia", 4.7110, -74.0721),
    ("Lima", "Peru", -12.0464, -77.0428),
    ("Cidade do Cabo", "África do Sul", -33.9249, 18.4241),
    ("Nairóbi", "Quênia", -1.2921, 36.8219),
    ("Cairo", "Egito", 30.0444, 31.2357),
    ("Marrakech", "Marrocos", 31.6295, -7.9811),
    ("Dubai", "Emirados Árabes Unidos", 25.2048, 55.2708),
    ("Istambul", "Turquia", 41.0082, 28.9784),
    ("Moscou", "Rússia", 55.7558, 37.6173),
    ("Nova Deli", "Índia", 28.6139, 77.2090),
    ("Mumbai", "Índia", 19.0760, 72.8777),
    ("Bangkok", "Tailândia", 13.7563, 100.5018),
    ("Singapura", "Singapura", 1.3521, 103.8198),
    ("Hong Kong", "China", 22.3193, 114.1694),
    ("Tóquio", "Japão", 35.6762, 139.6503),
    ("Seul", "Coreia do Sul", 37.5665, 126.9780),
    ("Sydney", "Austrália", -33.8688, 151.2093),
    ("Melbourne", "Austrália", -37.8136, 144.9631),
    ("Auckland", "Nova Zelândia", -36.8485, 174.7633),
    ("Honolulu", "EUA", 21.3069, -157.8583),
    ("Barcelona", "Espanha", 41.3851, 2.1734),
    ("Praga", "República Tcheca", 50.0755, 14.4378),
    ("Atenas", "Grécia", 37.9838, 23.7275),
    ("Bali", "Indonésia", -8.3405, 115.0920),
    ("Montreal", "Canadá", 45.5019, -73.5674),
    ("Austin", "EUA", 30.2672, -97.7431),
]


def julian_day_utc(birthdate: datetime, hour_utc: Optional[float] = None) -> float:
    """Julian day for the birth instant. Defaults to 12:00 UTC (noon) when no
    time is supplied, per the app's stated convention."""
    hour = 12.0 if hour_utc is None else hour_utc
    return ephem.julian_day(birthdate.year, birthdate.month, birthdate.day, hour)


def _normalize_lon(lon: float) -> float:
    return ((lon + 180) % 360) - 180


def _planet_equatorial(jd_ut: float, planet_key: str) -> Tuple[float, float]:
    """Returns (RA in degrees, Dec in degrees)."""
    return ephem.get_planet_radec(jd_ut, planet_key)


def compute_planet_lines(jd_ut: float, planet_key: str) -> Dict:
    """Computes the MC/IC meridian longitudes and a sampled AC/DC curve
    (list of lat/lon points) for one planet at the given birth instant."""
    ra_deg, dec_deg = _planet_equatorial(jd_ut, planet_key)
    ra_h = ra_deg / 15.0
    gst_h = ephem.gmst_hours(jd_ut)  # Greenwich sidereal time, in hours

    mc_lon = _normalize_lon((ra_h - gst_h) * 15.0)
    ic_lon = _normalize_lon(mc_lon + 180.0)

    ac_points: List[Tuple[float, float]] = []
    dc_points: List[Tuple[float, float]] = []
    dec_rad = math.radians(dec_deg)

    for lat in range(-66, 67, 1):
        lat_rad = math.radians(lat)
        tan_product = math.tan(lat_rad) * math.tan(dec_rad)
        if abs(tan_product) > 1:
            continue  # planet never rises/sets at this latitude (circumpolar/never-visible)
        h0 = math.degrees(math.acos(-tan_product))

        # Rising (Ascendant): hour angle = -h0 ; Setting (Descendant): +h0
        for label, hour_angle, bucket in (("AC", -h0, ac_points), ("DC", h0, dc_points)):
            lst_h = ra_h + hour_angle / 15.0
            lon = _normalize_lon((lst_h - gst_h) * 15.0)
            bucket.append((float(lat), lon))

    return {
        "mc_lon": mc_lon,
        "ic_lon": ic_lon,
        "ac_points": ac_points,
        "dc_points": dc_points,
    }


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _distance_to_meridian_km(city_lat, city_lon, meridian_lon) -> float:
    # Closest point on a full meridian to a given city is at the same latitude.
    return _haversine_km(city_lat, city_lon, city_lat, meridian_lon)


def _distance_to_curve_km(city_lat, city_lon, points: List[Tuple[float, float]]) -> float:
    if not points:
        return float("inf")
    best = float("inf")
    for plat, plon in points:
        d = _haversine_km(city_lat, city_lon, plat, plon)
        if d < best:
            best = d
    return best


def all_planet_lines(jd_ut: float) -> Dict[str, Dict]:
    return {name: compute_planet_lines(jd_ut, pid) for name, pid in PLANETS.items()}


def city_line_distances(city_lat: float, city_lon: float, lines: Dict[str, Dict]) -> List[Dict]:
    """For one city, returns the distance (km) from that city to every
    planet's four angular lines."""
    results = []
    for planet, data in lines.items():
        candidates = [
            ("MC", _distance_to_meridian_km(city_lat, city_lon, data["mc_lon"])),
            ("IC", _distance_to_meridian_km(city_lat, city_lon, data["ic_lon"])),
            ("AC", _distance_to_curve_km(city_lat, city_lon, data["ac_points"])),
            ("DC", _distance_to_curve_km(city_lat, city_lon, data["dc_points"])),
        ]
        for angle, dist_km in candidates:
            results.append({"planet": planet, "angle": angle, "distance_km": dist_km})
    return results


def best_places_to_live(
    jd_ut: float,
    top_n: int = 3,
    orb_km: float = 900.0,
    max_lines_per_city: int = 3,
    jd_ut_partner: Optional[float] = None,
) -> List[Dict]:
    """
    Ranks WORLD_CITIES by proximity to favorable planetary lines (Sun, Moon,
    Venus, Jupiter). If jd_ut_partner is given, cities are scored on how well
    they work for BOTH charts (average of each person's best favorable-line
    distance) — a simple couple's astrocartography overlay.
    """
    lines_p1 = all_planet_lines(jd_ut)
    lines_p2 = all_planet_lines(jd_ut_partner) if jd_ut_partner is not None else None

    scored = []
    for name, country, lat, lon in WORLD_CITIES:
        dist_p1 = city_line_distances(lat, lon, lines_p1)
        fav_p1 = sorted(
            [d for d in dist_p1 if d["planet"] in FAVORABLE_PLANETS],
            key=lambda d: d["distance_km"],
        )
        best_p1 = fav_p1[0]["distance_km"] if fav_p1 else float("inf")

        if lines_p2 is not None:
            dist_p2 = city_line_distances(lat, lon, lines_p2)
            fav_p2 = sorted(
                [d for d in dist_p2 if d["planet"] in FAVORABLE_PLANETS],
                key=lambda d: d["distance_km"],
            )
            best_p2 = fav_p2[0]["distance_km"] if fav_p2 else float("inf")
            score = (best_p1 + best_p2) / 2.0
        else:
            fav_p2 = []
            score = best_p1

        scored.append({
            "name": name,
            "country": country,
            "lat": lat,
            "lon": lon,
            "score_km": score,
            "favorable_lines_p1": [d for d in fav_p1 if d["distance_km"] <= orb_km][:max_lines_per_city],
            "favorable_lines_p2": [d for d in fav_p2 if d["distance_km"] <= orb_km][:max_lines_per_city],
        })

    scored.sort(key=lambda c: c["score_km"])
    return scored[:top_n]


def format_line_label(planet: str, angle: str) -> str:
    return f"{planet} em {ANGLE_NAMES[angle]}"
